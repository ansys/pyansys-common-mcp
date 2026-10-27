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
from multiprocessing.connection import Client, Connection
from pathlib import Path

# Subprocess is needed for managing the persistent Python session
import subprocess  # nosec B404
import sys
import tempfile
import threading
import time
from typing import Annotated, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, validate_call

from ansys.common.mcp.logging_config import get_logger

logger = get_logger(__name__)


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


class _ExecutionResult(BaseModel):
    """Captured Python output and status returned over the control connection."""

    id: str
    success: bool
    is_complete: bool
    stdout: str
    stderr: str


class PersistentPythonSession:
    r"""Maintains a persistent Python subprocess for stateful code execution.

    This class allows multiple code snippets to be executed in the same
    Python session, preserving variables, imports, and state between
    executions. This is essential for LLM workflows where code is generated
    and executed in multiple steps.

    Native output logs are owned by a temporary directory created during
    initialization and removed on shutdown. Starting again creates a fresh directory.

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
        self._logs = tempfile.TemporaryDirectory(prefix="python-session-")
        self._control: Optional[Connection] = None
        self._log_directory = Path(self._logs.name)
        self._is_running = False
        self._execution_lock = threading.Lock()
        self._pending: Optional[str] = None
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

            if not self._log_directory.exists():
                self._logs = tempfile.TemporaryDirectory(prefix="python-session-")
                self._log_directory = Path(self._logs.name)
            self._pending = None
            family = "AF_PIPE" if sys.platform == "win32" else "AF_UNIX"
            address = (
                rf"\\.\pipe\python-session-{uuid4().hex}"
                if family == "AF_PIPE"
                else str(self._log_directory / "control")
            )
            worker = Path(__file__).with_name("_interactive_python.py")
            with (
                (self._log_directory / "stdout.log").open("wb") as stdout,
                (self._log_directory / "stderr.log").open("wb") as stderr,
            ):
                self.process = subprocess.Popen(
                    [self.python_executable, "-u", "-X", "utf8", str(worker), address, family],
                    stdin=subprocess.PIPE,
                    stdout=stdout,
                    stderr=stderr,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,  # Line buffered
                    cwd=self.working_directory,
                )  # nosec B603

            self._is_running = True

            deadline = time.monotonic() + 5
            while True:
                try:
                    self._control = Client(address, family=family)
                    break
                except OSError:
                    if self.process.poll() is not None or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.01)
            logger.debug("Native Python output logs: %s", self._log_directory)

            ready = self.execute("")
            if not ready["success"]:
                self.stop()
                return ready

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
            if self._is_running:
                self.stop()
            else:
                self._logs.cleanup()
            self._is_running = False
            return {
                "success": False,
                "error": error_msg,
            }

    @validate_call(config=ConfigDict(strict=True, allow_inf_nan=False))
    def execute(
        self,
        code: str,
        timeout: Annotated[float, Field(gt=0)] = 30,
    ) -> dict[str, Any]:
        """Execute Python code in the persistent session.

        Parameters
        ----------
        code : str
            Python code to execute.
        timeout : float, default: 30.0
            Maximum client wait in seconds. Execution continues after a timeout.
            Use ``wait_for_result()`` to collect its pending result. A new execution
            discards the previous result if it has finished, or is rejected if still running.

        Returns
        -------
        dict[str, Any]
            Dictionary containing:
            - 'success': Boolean indicating if execution succeeded
            - 'stdout': string with standard output
            - 'stderr': string with standard error
            - 'error': string with error message (if execution failed)

        """
        if not self._is_running or self.process is None:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": "Session is not running. Call 'start()' first.",
            }

        with self._execution_lock:
            if self._pending:
                previous = self._collect_result(0)
                if self._pending:
                    return previous
                logger.debug("Discarding completed pending execution result.")
            request_id = uuid4().hex
            try:
                logger.debug(f"Executing code: {code[:100]}...")
                if self.process.stdin is None:
                    return self._execution_error("Process stdin is not available.")
                self.process.stdin.write(json.dumps({"id": request_id, "code": code}) + "\n")
                self.process.stdin.flush()
            except (OSError, ValueError) as exc:
                return self._execution_error(f"Error sending code: {exc}")
            self._pending = request_id
            return self._collect_result(timeout)

    def _execution_error(self, message: str) -> dict[str, Any]:
        """Return an explicit failure without discarding the pending request."""
        logger.error(message)
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": message,
        }

    @validate_call(config=ConfigDict(strict=True, allow_inf_nan=False))
    def wait_for_result(self, timeout: Annotated[float, Field(gt=0)] = 30) -> dict[str, Any]:
        """Continue waiting for a timed-out execution without resubmitting code."""
        with self._execution_lock:
            if not self._pending:
                return self._execution_error("No execution result is pending.")
            return self._collect_result(timeout)

    def _collect_result(self, timeout: float) -> dict[str, Any]:
        """Wait for one validated response belonging to the pending request."""
        if self._control is None:
            return self._execution_error("Python control connection is not available.")
        try:
            if not self._control.poll(timeout):
                if timeout == 0:
                    return self._execution_error(
                        "Execution result pending. "
                        "Call wait_for_result() before submitting new code."
                    )
                return self._execution_error(
                    f"Code execution timed out after {timeout} seconds. "
                    "Execution continues; call wait_for_result()."
                )
            result = _ExecutionResult.model_validate_json(self._control.recv_bytes(), strict=True)
        except (EOFError, OSError, ValueError) as exc:
            return self._execution_error(f"Python control response failed: {exc}")
        if result.id != self._pending:
            return self._execution_error(
                f"Python response ID {result.id!r} "
                f"does not match pending request {self._pending!r}."
            )
        self._pending = None
        error = ""
        if not result.is_complete:
            error = "Incomplete Python source. Submit a complete snippet."
        elif not result.success:
            error = result.stderr or "Python execution failed."
        if error:
            logger.error(error)
        return {
            "success": not error,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": error,
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
                "error": "Session is not running.",
            }

        try:
            logger.info("Stopping persistent Python session.")

            # EOF stops the worker after any current execution finishes.
            if self.process and self.process.stdin:
                try:
                    self.process.stdin.close()
                except Exception as e:
                    logger.warning(f"Error sending exit command: {e}")

            # Wait for process to terminate
            if self.process:
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully. Forcing termination.")
                    self.process.kill()
                    self.process.wait()

            if self._control is not None:
                self._control.close()
                self._control = None
            self._logs.cleanup()
            self._is_running = False
            self._pending = None
            logger.info("Persistent Python session stopped.")

            return {
                "success": True,
                "message": "Session stopped successfully.",
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

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.stop()
        return False
