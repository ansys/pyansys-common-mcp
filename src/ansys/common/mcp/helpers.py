import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional
import threading
import queue
from ansys.common.mcp.logging_config import get_logger

logger = get_logger(__name__)


def exception_wrapper(func: Callable[[], Any]) -> Any | str:
    """Wrap to catch exceptions and return error messages."""
    try:
        return func()
    except ImportError as e:
        error_msg = f"Error when running {str(func)}: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error when running {str(func)}: {e}"
        logger.error(error_msg)
        return error_msg


class PersistentPythonSession:
    """Maintains a persistent Python subprocess for stateful code execution.

    This class allows multiple code snippets to be executed in the same
    Python session, preserving variables, imports, and state between
    executions. This is essential for LLM workflows where code is generated
    and executed in multiple steps.

    Parameters
    ----------
    python_executable : Optional[str]
        Path to the Python executable to use. If None, uses sys.executable.
    startup_code : Optional[str]
        Python code to execute when the session starts (e.g., imports).
    working_directory : Optional[str]
        Working directory for the Python process. If None, uses the current directory.

    Examples
    --------
    Create a persistent session and execute multiple steps:

    >>> session = PersistentPythonSession()
    >>> session.start()
    >>> 
    >>> # Step 1: Define variables
    >>> result = session.execute("x = 10; y = 20")
    >>> 
    >>> # Step 2: Use those variables
    >>> result = session.execute("z = x + y; print(z)")
    >>> print(result['stdout'])  # 30
    >>> 
    >>> session.stop()

    Use with custom Python executable:

    >>> session = PersistentPythonSession(
    ...     python_executable="/path/to/venv/bin/python",
    ...     startup_code="import numpy as np\\nimport pandas as pd"
    ... )
    """

    def __init__(
        self,
        python_executable: Optional[str] = None,
        startup_code: Optional[str] = None,
        working_directory: Optional[str] = None,
    ):
        """Initialize the persistent Python session."""
        self.python_executable = python_executable or sys.executable
        self.startup_code = startup_code
        self.working_directory = working_directory
        self.process: Optional[subprocess.Popen] = None
        self._output_thread: Optional[threading.Thread] = None
        self._error_thread: Optional[threading.Thread] = None
        self._output_queue: queue.Queue = queue.Queue()
        self._error_queue: queue.Queue = queue.Queue()
        self._is_running = False
        self._execution_lock = threading.Lock()

    def start(self) -> dict[str, Any]:
        """Start the persistent Python session.

        Returns
        -------
        dict[str, Any]
            Dictionary with success status and any startup messages.
        """
        if self._is_running:
            return {
                "success": False,
                "error": "Session is already running",
            }

        # Validate Python executable
        if not Path(self.python_executable).exists():
            error_msg = f"Python executable not found: {self.python_executable}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

        try:
            logger.info(f"Starting persistent Python session: {self.python_executable}")

            # Start Python in interactive mode with unbuffered I/O
            self.process = subprocess.Popen(
                [self.python_executable, "-u", "-i"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=self.working_directory,
            )

            self._is_running = True

            # Start threads to read output
            self._output_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stdout, self._output_queue),
                daemon=True,
            )
            self._error_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stderr, self._error_queue),
                daemon=True,
            )

            self._output_thread.start()
            self._error_thread.start()

            # Clear initial Python prompt
            self._drain_queues(timeout=0.5)

            # Execute startup code if provided
            if self.startup_code:
                logger.info("Executing startup code")
                startup_result = self.execute(self.startup_code)
                if not startup_result["success"]:
                    logger.warning(f"Startup code failed: {startup_result.get('error')}")

            logger.info("Persistent Python session started successfully")
            return {
                "success": True,
                "message": "Session started successfully",
                "python_executable": self.python_executable,
            }

        except Exception as e:
            error_msg = f"Failed to start Python session: {str(e)}"
            logger.error(error_msg)
            self._is_running = False
            return {
                "success": False,
                "error": error_msg,
            }

    def execute(self, code: str, timeout: float = 30.0) -> dict[str, Any]:
        """Execute Python code in the persistent session.

        Parameters
        ----------
        code : str
            Python code to execute.
        timeout : float
            Maximum execution time in seconds (default: 30.0).

        Returns
        -------
        dict[str, Any]
            Dictionary containing:
            - 'success': bool indicating if execution succeeded
            - 'stdout': str with standard output
            - 'stderr': str with standard error
            - 'error': str with error message (if execution failed)
        """
        if not self._is_running or self.process is None:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": "Session is not running. Call start() first.",
            }

        with self._execution_lock:
            try:
                # Clear any pending output
                self._drain_queues(timeout=0.1)

                # Send code to Python process
                # Use a unique marker to detect when execution is complete
                marker = "___EXECUTION_COMPLETE___"
                code_with_marker = f"{code}\nprint('{marker}')\n"

                logger.debug(f"Executing code: {code[:100]}...")
                self.process.stdin.write(code_with_marker)
                self.process.stdin.flush()

                # Collect output until we see the marker or timeout
                stdout_lines = []
                stderr_lines = []
                start_time = __import__('time').time()

                while True:
                    elapsed = __import__('time').time() - start_time
                    if elapsed > timeout:
                        error_msg = f"Code execution timed out after {timeout} seconds"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "stdout": "\n".join(stdout_lines),
                            "stderr": "\n".join(stderr_lines),
                            "error": error_msg,
                        }

                    # Read from stdout
                    try:
                        line = self._output_queue.get(timeout=0.1)
                        if marker in line:
                            # Remove the marker line and stop
                            line = line.replace(marker, "").strip()
                            if line:
                                stdout_lines.append(line)
                            break
                        stdout_lines.append(line.rstrip())
                    except queue.Empty:
                        pass

                    # Read from stderr
                    try:
                        line = self._error_queue.get(timeout=0.01)
                        stderr_lines.append(line.rstrip())
                    except queue.Empty:
                        pass

                stdout_text = "\n".join(stdout_lines)
                stderr_text = "\n".join(stderr_lines)

                # Check if there were any errors
                has_error = bool(stderr_text) and any(
                    keyword in stderr_text.lower()
                    for keyword in ["error", "exception", "traceback"]
                )

                if has_error:
                    logger.warning(f"Code execution had errors: {stderr_text[:200]}")

                return {
                    "success": not has_error,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "error": stderr_text if has_error else "",
                }

            except Exception as e:
                error_msg = f"Error during code execution: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "error": error_msg,
                }

    def stop(self) -> dict[str, Any]:
        """Stop the persistent Python session.

        Returns
        -------
        dict[str, Any]
            Dictionary with success status and cleanup messages.
        """
        if not self._is_running:
            return {
                "success": False,
                "error": "Session is not running",
            }

        try:
            logger.info("Stopping persistent Python session")

            # Send exit command
            if self.process and self.process.stdin:
                try:
                    self.process.stdin.write("exit()\n")
                    self.process.stdin.flush()
                except Exception:
                    pass

            # Wait for process to terminate
            if self.process:
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully, forcing termination")
                    self.process.kill()
                    self.process.wait()

            self._is_running = False
            logger.info("Persistent Python session stopped")

            return {
                "success": True,
                "message": "Session stopped successfully",
            }

        except Exception as e:
            error_msg = f"Error stopping session: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

    def restart(self) -> dict[str, Any]:
        """Restart the persistent Python session.
        
        Stops the current session (if running) and starts a new one.
        All session state (variables, imports) will be lost except
        what's recreated by startup_code.
        
        This method is intended for manual restarts only, for example when
        the session becomes unresponsive or when you want to reset the state.
        Command history and other application state should be managed at the
        application context level, not in the session itself.
        
        Returns
        -------
        dict[str, Any]
            Dictionary with success status and restart messages.
            
        Examples
        --------
        Basic restart:
        
        >>> session = PersistentPythonSession()
        >>> session.start()
        >>> # ... do some work ...
        >>> result = session.restart()
        >>> if result["success"]:
        ...     print("Session restarted")
        
        In an MCP tool with command replay:
        
        >>> # Get context
        >>> ctx = get_context()
        >>> app_context = ctx.fastmcp._lifespan_result
        >>> 
        >>> # Restart session
        >>> restart_result = app_context.python_session.restart()
        >>> 
        >>> # Optionally replay command history
        >>> if restart_result["success"] and app_context.command_history:
        ...     for cmd in app_context.command_history:
        ...         app_context.python_session.execute(cmd)
        
        Notes
        -----
        - This is a manual operation - automatic restart on crashes is NOT implemented
        - Session state is lost (variables, non-startup imports, etc.)
        - The startup_code is re-executed on restart
        - Consider managing command_history at the context level for replay capability
        """
        logger.info("Restarting persistent Python session...")
        
        # Stop existing session if running
        if self._is_running:
            logger.debug("Stopping existing session before restart")
            stop_result = self.stop()
            if not stop_result["success"]:
                logger.warning(f"Error during stop phase of restart: {stop_result.get('error')}")
                # Continue anyway - we'll try to start fresh
        
        # Start new session
        logger.debug("Starting new session")
        start_result = self.start()
        
        if start_result["success"]:
            logger.info("Persistent Python session restarted successfully")
            return {
                "success": True,
                "message": "Session restarted successfully",
                "python_executable": self.python_executable,
            }
        else:
            error_msg = f"Failed to restart session: {start_result.get('error')}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

    def is_running(self) -> bool:
        """Check if the session is currently running.

        Returns
        -------
        bool
            True if session is running, False otherwise.
        """
        return self._is_running and self.process is not None and self.process.poll() is None

    def _read_stream(self, stream, output_queue: queue.Queue):
        """Read from a stream and put lines into a queue.

        Parameters
        ----------
        stream
            The stream to read from (stdout or stderr).
        output_queue : queue.Queue
            Queue to put the read lines into.
        """
        try:
            for line in iter(stream.readline, ''):
                if line:
                    output_queue.put(line)
                if not self._is_running:
                    break
        except Exception as e:
            logger.error(f"Error reading stream: {e}")

    def _drain_queues(self, timeout: float = 0.1):
        """Drain both output queues to clear any pending output.

        Parameters
        ----------
        timeout : float
            Maximum time to spend draining queues.
        """
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                self._output_queue.get_nowait()
            except queue.Empty:
                break
        
        start = time.time()
        while time.time() - start < timeout:
            try:
                self._error_queue.get_nowait()
            except queue.Empty:
                break

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
