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
import re

# Subprocess is needed for managing the persistent Python session
import subprocess  # nosec B404
import sys
import threading
import time
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, validate_call

from ansys.common.mcp.logging_config import get_logger

logger = get_logger(__name__)

_COMMENT_PATTERN = re.compile(r"^\s*#")
_CONTINUATION_BLOCK_PATTERN = re.compile(r"^\s*(?:else|elif|except|finally)\b")


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


def _prepare_repl_code(code: str) -> str:
    """Prepare a snippet for running in the interactive REPL.

    The persistent session uses an interactive Python interpreter to execute
    code, sending the text to the Python interpreter's `stdin`. The REPL
    obeys these rules:

    * a blank line inside an indented block terminates it early
    * an indented block is only executed once a blank line is encountered

    Therefore the text needs to be prepared to correctly drive the REPL:

    * blank lines inside indented blocks are replaced by `#` so the block
    does not terminate prematurely
    * an extra blank line is inserted at the end of the last indented block
    to trigger the execution of that block

    Parameters
    ----------
    code : str
        Python source to send to the interactive session.

    Returns
    -------
    str
        The prepared source code.
    """
    lines = code.splitlines()
    if not lines:
        return code

    prepared_repl_code: list[str] = []

    # Block of code always start without indentation
    # (if not `IndentationError: unexpected indent`
    # will be generated anyway)
    is_current_line_indented = False

    for line in lines:
        is_comment_line = _COMMENT_PATTERN.match(line)
        if is_comment_line:
            # leave comment lines as is
            # do not consider them to decide if enter is required
            prepared_repl_code.append(line)
            continue

        if not line.strip():
            # empty line, change to comment to prevent
            # inadvertent execution
            prepared_repl_code.append(line + "#")
            continue

        is_previous_line_indented = is_current_line_indented

        is_current_line_indented = line.startswith((" ", "\t"))

        is_continuation = _CONTINUATION_BLOCK_PATTERN.match(line)
        if not is_continuation:
            is_end_of_block = not is_current_line_indented and is_previous_line_indented
            if is_end_of_block:
                # end of the block, insert blank line to trigger the REPL evaluation
                prepared_repl_code.append("")

        prepared_repl_code.append(line)

    if is_current_line_indented:
        # trigger the REPL evaluation if ending on an indented block
        prepared_repl_code.append("")

    return "\n".join(prepared_repl_code)


class _CodeTerminationMarker(BaseModel):
    """Boundary emitted by the worker on each output stream."""

    marker: Literal["___EXECUTION_COMPLETE___"]
    success: bool
    is_complete: bool


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
        self._pending = False
        self._collected: dict[str, list[str]] = {"stdout": [], "stderr": []}
        self._markers: dict[str, _CodeTerminationMarker] = {}
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

            self._output_queue = queue.Queue()
            self._error_queue = queue.Queue()
            self._pending = False
            worker = Path(__file__).with_name("_interactive_python.py")
            self.process = subprocess.Popen(
                [self.python_executable, "-u", str(worker)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,  # Line buffered
                cwd=self.working_directory,
            )  # nosec B603

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
        no_output_timeout: Optional[Annotated[float, Field(gt=0)]] = 1.2,
    ) -> dict[str, Any]:
        """Execute Python code in the persistent session.

        Parameters
        ----------
        code : str
            Python code to execute.
        timeout : float, default: 30.0
            Maximum client wait in seconds. Execution continues after a timeout.
            Collect its pending result with ``wait_for_result()`` before submitting more code.
        no_output_timeout : float or None, default: 1.2
            Maximum number of seconds to wait without receiving any output before
            returning a pending-execution error. Execution continues in the worker.
            Set to ``None`` to wait solely for the overall client timeout.

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
                return self._execution_error(
                    "Execution result pending. Call wait_for_result() before submitting new code."
                )
            try:
                logger.debug(f"Executing code: {code[:100]}...")
                if self.process.stdin is None:
                    return self._execution_error("Process stdin is not available.")
                self.process.stdin.write(json.dumps({"code": code}) + "\n")
                self.process.stdin.flush()
            except (OSError, ValueError) as exc:
                return self._execution_error(f"Error sending code: {exc}")
            self._pending = True
            self._collected = {"stdout": [], "stderr": []}
            self._markers = {}
            return self._collect_result(timeout, no_output_timeout)

    def _execution_error(self, message: str) -> dict[str, Any]:
        """Return an explicit failure while retaining any pending output."""
        logger.error(message)
        return {
            "success": False,
            "stdout": "".join(self._collected["stdout"]),
            "stderr": "".join(self._collected["stderr"]),
            "error": message,
        }

    @validate_call(config=ConfigDict(strict=True, allow_inf_nan=False))
    def wait_for_result(self, timeout: Annotated[float, Field(gt=0)] = 30) -> dict[str, Any]:
        """Continue waiting for a timed-out execution without resubmitting code."""
        with self._execution_lock:
            if not self._pending:
                return self._execution_error("No execution result is pending.")
            return self._collect_result(timeout, None)

    def _collect_result(self, timeout: float, no_output_timeout: Optional[float]) -> dict[str, Any]:
        """Collect each stream through its validated boundary, retaining state on timeout."""
        deadline = time.monotonic() + timeout
        last_output = time.monotonic()
        while len(self._markers) < 2:
            for name, output_queue in (
                ("stdout", self._output_queue),
                ("stderr", self._error_queue),
            ):
                if name in self._markers:
                    continue
                try:
                    line = output_queue.get(timeout=min(0.01, max(0, deadline - time.monotonic())))
                except queue.Empty:
                    continue
                if line is None:
                    self._pending = False
                    return self._execution_error(f"Python session closed {name} before its marker.")
                last_output = time.monotonic()
                try:
                    marker = _CodeTerminationMarker.model_validate_json(line, strict=True)
                except ValidationError:
                    self._collected[name].append(line)
                else:
                    self._markers[name] = marker
                    # The worker inserts exactly one newline before the marker.
                    text = "".join(self._collected[name])
                    self._collected[name] = [text.removesuffix("\n")]
            if len(self._markers) == 2:
                break
            if time.monotonic() >= deadline:
                return self._execution_error(
                    f"Code execution timed out after {timeout} seconds. "
                    "Execution continues; call wait_for_result()."
                )
            if (
                no_output_timeout is not None
                and time.monotonic() - last_output >= no_output_timeout
            ):
                return self._execution_error(
                    "No output received before no_output_timeout. "
                    "Execution continues; call wait_for_result()."
                )
        self._pending = False
        marker = self._markers["stdout"]
        if marker != self._markers["stderr"]:
            return self._execution_error("Python session returned inconsistent completion markers.")
        error = ""
        if not marker.is_complete:
            error = "Incomplete Python source. Submit a complete snippet."
        elif not marker.success:
            error = "".join(self._collected["stderr"]) or "Python execution failed."
        if error:
            return self._execution_error(error)
        return {
            "success": True,
            "stdout": "".join(self._collected["stdout"]),
            "stderr": "".join(self._collected["stderr"]),
            "error": "",
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

            for thread in (self._output_thread, self._error_thread):
                if thread is not None:
                    thread.join(timeout=1)
            if self.process:
                for stream in (self.process.stdout, self.process.stderr):
                    if stream is not None:
                        stream.close()
            self._is_running = False
            self._pending = False
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
                if not self._is_running:
                    break
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
