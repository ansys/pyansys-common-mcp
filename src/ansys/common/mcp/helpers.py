# Copyright (C) 2025 - 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper utilities for the MCP server."""

import json
from pathlib import Path
import queue

# Subprocess is needed for managing the persistent Python session
import subprocess  # nosec B404
import sys
import threading
import time
from typing import Any, Final, Optional
import uuid

from ansys.common.mcp.logging_config import get_logger

from . import _interactive_python

logger = get_logger(__name__)

_MARKER_PREFIX: Final[str] = "___EXECUTION_COMPLETE___:"


def _sanitize_output(text: str) -> str:
    """Sanitize the output text to handle encoding issues.

    This function removes or replaces problematic Unicode characters that can cause
    encoding issues on Windows systems with limited character sets (such as charmap).

    Parameters
    ----------
    text : str
        Text to sanitize.

    Returns
    -------
    str
        Sanitized text with problematic characters removed or replaced.

    """
    if not isinstance(text, str):
        return text

    # Replace common problematic Unicode characters with ASCII alternatives
    replacements = {
        # Checkmarks and crosses
        "\u2713": "[OK]",  # checkmark
        "\u2717": "[X]",  # cross
        # Box drawing characters
        "\u2514": "\\",  # box drawing
        "\u2502": "|",  # box drawing
        "\u2500": "-",  # box drawing
        "\u2510": "\\",  # box drawing
        "\u250c": "/",  # box drawing
        "\u2518": "/",  # box drawing
        # Block elements
        "\u2588": "#",  # block
        "\u2589": "#",  # block
        "\u258a": "#",  # block
        "\u258c": "|",  # block
        "\u2590": "|",  # block
        # Superscript and subscript characters
        "\u00b9": "^1",  # superscript 1
        "\u00b2": "^2",  # superscript 2
        "\u00b3": "^3",  # superscript 3
        "\u2074": "^4",  # superscript 4
        "\u2075": "^5",  # superscript 5
        "\u2076": "^6",  # superscript 6
        "\u2077": "^7",  # superscript 7
        "\u2078": "^8",  # superscript 8
        "\u2079": "^9",  # superscript 9
        "\u2070": "^0",  # superscript 0
        # Other commonly problematic characters
        "\u2022": "*",  # bullet
        "\u2023": "*",  # triangular bullet
        "\u2219": "*",  # bullet operator
        "\u00a0": " ",  # non-breaking space
        "\u200b": "",  # zero-width space
        "\u200c": "",  # zero-width non-joiner
        "\u200d": "",  # zero-width joiner
        "\ufeff": "",  # zero-width no-break space
    }

    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)

    # Remove any remaining characters that can't be encoded in ASCII
    try:
        # Try to encode as ASCII to check for problematic characters
        text.encode("ascii")
    except UnicodeEncodeError:
        # If there are non-ASCII characters, replace them with a replacement character
        text = text.encode("ascii", errors="replace").decode("ascii")

    return text


class PersistentPythonSession:
    r"""Maintains a persistent Python subprocess for stateful code execution.

    This class allows multiple code snippets to be executed in the same
    Python session, preserving variables, imports, and state between
    executions. This is essential for LLM workflows where code is generated
    and executed in multiple steps.

    Parameters
    ----------
    python_executable : str, default: None
        Path to the Python executable to use. If ``None``, ``sys.executable`` is used.
    startup_code : str, default: None
        Python code to execute when the session starts (for example, imports).
    working_directory : str, default: None
        Working directory for the Python process. If ``None``, the current directory is used.

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
    >>> print(result["stdout"])  # 30
    >>>
    >>> session.stop()

    Use with custom Python executable:

    >>> session = PersistentPythonSession(
    ...     python_executable="/path/to/venv/bin/python",
    ...     startup_code="import numpy as np\\nimport pandas as pd",
    ... )

    Notes
    -----
    Code is executed with the permissions of the current user; this session is
    not a security sandbox.

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
        self.metadata: dict[str, Any] = {}

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
            worker = Path(_interactive_python.__file__).resolve()
            # `python_executable` was validated above to point to an existing file, the
            # worker path is resolved from this package (not user input), and no
            # `shell=True`/string command is involved, so there is no shell-injection
            # vector here despite the generic "subprocess call" warning.
            self.process = subprocess.Popen(
                [self.python_executable, "-u", "-X", "utf8", str(worker)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,  # Line buffered
                cwd=self.working_directory,
            )  # nosec B603

            self._output_queue = queue.Queue()
            self._error_queue = queue.Queue()
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

            # Execute startup code if provided
            if self.startup_code:
                logger.info("Executing startup code...")
                startup_result = self.execute(self.startup_code)
                if not startup_result["success"]:
                    logger.warning(f"Startup code failed: {startup_result.get('error')}")

            logger.info("Persistent Python session started successfully.")
            return {
                "success": True,
                "message": "Session started successfully.",
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

    def execute(
        self, code: str, timeout: int = 30, no_output_timeout: Optional[float] = 1.2
    ) -> dict[str, Any]:
        """Execute Python code in the persistent session.

        Parameters
        ----------
        code : str
            Python code to execute.
        timeout : float, default: 30.0
            Maximum execution time in seconds.
        no_output_timeout : float or None, default: 1.2
            Maximum number of seconds to wait without receiving any output before
            stopping collection. This prevents infinite loops if the completion
            marker is never found. Set to ``None`` to disable this safety check.

        Returns
        -------
        dict[str, Any]
            Dictionary containing:
            - 'success': Boolean indicating if execution succeeded
            - 'stdout': string with standard output, including a final expression
              displayed as it would be in a Python interactive session
            - 'stderr': string with standard error
            - 'error': string with error message (if execution failed)

        Notes
        -----
        Timeouts stop output collection, not the running code. The worker and
        session state are retained.

        """
        if not self._is_running or self.process is None:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": "Session is not running. Call 'start()' first.",
            }

        if no_output_timeout is not None and (
            not isinstance(no_output_timeout, (int, float))
            or no_output_timeout <= 0
            or no_output_timeout != no_output_timeout  # NaN check
        ):
            raise ValueError(
                f"no_output_timeout must be a positive number or None, got {no_output_timeout!r}."
            )

        with self._execution_lock:
            request_sent = False
            try:
                if not self.is_running():
                    raise RuntimeError("Python worker is not running. Restart the session.")

                self._drain_queues(timeout=0.1)
                # Send code to Python process
                logger.debug(f"Executing code: {code[:100]}...")
                if self.process.stdin is None:
                    self._terminate_process()
                    return {
                        "success": False,
                        "stdout": "",
                        "stderr": "",
                        "error": "Process stdin is not available.",
                    }
                request_id = uuid.uuid4().hex
                request = {"action": "execute", "code": code, "request_id": request_id}
                request_sent = True
                self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
                self.process.stdin.flush()

                stdout_lines: list[str] = []
                stderr_lines: list[str] = []
                start_time = time.monotonic()
                last_output_time = start_time
                completed: dict[str, bool] = {}
                closed: set[str] = set()
                marker = f"{_MARKER_PREFIX}{request_id}:"
                failure = ""
                idle_expired = False
                streams = (
                    ("stdout", self._output_queue, stdout_lines),
                    ("stderr", self._error_queue, stderr_lines),
                )

                while len(completed) < 2:
                    received_output = False
                    for name, output_queue, lines in streams:
                        if name in completed or name in closed:
                            continue
                        for _ in range(256):
                            try:
                                line = output_queue.get_nowait()
                            except queue.Empty:
                                break
                            received_output = True
                            if line is None:
                                closed.add(name)
                                break
                            if line.rstrip("\r\n") in (marker + "true", marker + "false"):
                                completed[name] = line.rstrip("\r\n") == marker + "true"
                                # The worker inserts one newline to frame unterminated output.
                                if lines:
                                    lines[-1] = lines[-1].removesuffix("\n")
                                break
                            lines.append(line)

                    if len(completed) == 2:
                        break
                    if closed - completed.keys():
                        failure = (
                            "Python worker closed its output before completing execution. "
                            "Restart the session."
                        )
                        break
                    now = time.monotonic()
                    if now - start_time > timeout:
                        failure = f"Code execution timed out after {timeout} seconds."
                        break
                    if received_output:
                        last_output_time = time.monotonic()
                    elif (
                        no_output_timeout is not None and now - last_output_time > no_output_timeout
                    ):
                        logger.warning("No data received for extended period. Stopping collection.")
                        idle_expired = True
                        break
                    if not received_output:
                        time.sleep(0.005)

                stdout_text = "".join(stdout_lines)
                stderr_text = "".join(stderr_lines)
                if failure:
                    logger.error(failure)
                    if closed:
                        self._terminate_process()
                    return {
                        "success": False,
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "error": failure,
                    }
                if idle_expired:
                    # Preserve the existing idle-timeout result until timeout policy is revised.
                    success = not any(
                        keyword in stderr_text.lower()
                        for keyword in ("error", "exception", "traceback")
                    )
                elif completed["stdout"] != completed["stderr"]:
                    raise RuntimeError("Worker returned inconsistent execution status.")
                else:
                    success = completed["stdout"]
                if not success:
                    logger.warning(f"Code execution failed: {stderr_text[:200]}")

                return {
                    "success": success,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "error": stderr_text if not success else "",
                }

            except Exception as e:
                if request_sent:
                    self._terminate_process()
                error_msg = f"Error during code execution: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "error": error_msg,
                }

    def _terminate_process(self) -> Optional[int]:
        """Terminate the child process after a failed execution."""
        self._is_running = False
        if self.process is None or self.process.poll() is not None:
            return None if self.process is None else self.process.returncode

        try:
            self.process.terminate()
        except OSError:
            if self.process.poll() is None:
                raise
            return self.process.returncode
        try:
            return self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.kill()
            return self.process.wait()

    def stop(self) -> dict[str, Any]:
        """Stop the persistent Python session.

        Returns
        -------
        dict[str, Any]
            Dictionary with success status and cleanup messages.

        """
        with self._execution_lock:
            if not self._is_running or self.process is None:
                return {
                    "success": False,
                    "error": "Session is not running.",
                }

            logger.info("Stopping persistent Python session.")
            process = self.process
            try:
                return_code = process.poll()
                if return_code is None:
                    if process.stdin is None:
                        raise OSError("Worker stdin is not available.")
                    shutdown_request = {"action": "shutdown", "request_id": uuid.uuid4().hex}
                    process.stdin.write(json.dumps(shutdown_request) + "\n")
                    process.stdin.flush()
                    process.stdin.close()
                    return_code = process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired) as exc:
                logger.warning(f"Python worker did not stop gracefully: {exc}")
                self._terminate_process()
                return {
                    "success": False,
                    "error": "Python worker required forced termination.",
                }
            finally:
                self._is_running = False

            if return_code != 0:
                error_msg = f"Python worker exited with status {return_code}."
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

            logger.info("Persistent Python session stopped.")
            return {
                "success": True,
                "message": "Session stopped successfully.",
            }

    def restart(self) -> dict[str, Any]:
        """Restart the persistent Python session.

        Stops the current session (if running) and starts a new one.
        All session state (variables, imports) are lost except
        what's recreated by ``startup_code``.

        This method is intended for manual restarts only. For example, use it when
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
        - This is a manual operation. Automatic restart on crashes is NOT implemented.
        - Session state is lost (including variables and non-startup imports).
        - The ``startup_code`` is re-executed on restart.
        - Consider managing command_history at the context level for replay capability

        """
        logger.info("Restarting persistent Python session...")

        # Stop existing session if running
        if self._is_running:
            logger.debug("Stopping existing session before restart.")
            stop_result = self.stop()
            if not stop_result["success"]:
                logger.warning(f"Error during stop phase of restart: {stop_result.get('error')}")
                # Continue anyway - we'll try to start fresh

        # Start new session
        logger.debug("Starting new session.")
        start_result = self.start()

        if start_result["success"]:
            logger.info("Persistent Python session restarted successfully.")
            return {
                "success": True,
                "message": "Session restarted successfully.",
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
            ``True`` if session is running, ``False`` otherwise.

        """
        return self._is_running and self.process is not None and self.process.poll() is None

    def _read_stream(self, stream, output_queue: queue.Queue):
        """Read from a stream and put lines into a queue.

        Parameters
        ----------
        stream
            Stream to read from (stdout or stderr).
        output_queue : queue.Queue
            Queue to put the read lines into.

        """
        try:
            for line in iter(stream.readline, ""):
                if line:
                    output_queue.put(line)
        except Exception as e:
            logger.error(f"Error reading stream: {e}")
        finally:
            output_queue.put(None)

    def _drain_queues(self, timeout: float = 0.1):
        """Drain both output and error queues to clear any pending output.

        Parameters
        ----------
        timeout : float, default: 0.1
            Maximum time to spend draining queues in seconds.

        """
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

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.stop()
        return False
