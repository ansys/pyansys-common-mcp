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

"""Unit tests for helpers module."""

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile

import pytest

from ansys.common.mcp.helpers import PersistentPythonSession

# ============================================================================
# PersistentPythonSession Unit Tests
# ============================================================================


class TestPersistentPythonSessionInitialization:
    """Test suite for PersistentPythonSession initialization and configuration.

    Tests that sessions are correctly initialized with various parameters.
    """

    def test_default_initialization(self):
        """Test that default initialization sets correct values."""
        session = PersistentPythonSession()

        assert session.python_executable == sys.executable
        assert session.startup_code is None
        assert session.working_directory is None
        assert session.process is None
        assert not session._is_running
        assert session.metadata == {}

    def test_custom_python_executable(self):
        """Test initialization with custom python executable path."""
        executable = "/custom/python"
        session = PersistentPythonSession(python_executable=executable)

        assert session.python_executable == executable

    def test_startup_code_parameter(self):
        """Test initialization with startup code."""
        startup_code = "import numpy as np\nx = 42"
        session = PersistentPythonSession(startup_code=startup_code)

        assert session.startup_code == startup_code

    def test_working_directory_parameter(self):
        """Test initialization with working directory."""
        work_dir = "/tmp/workspace"
        session = PersistentPythonSession(working_directory=work_dir)

        assert session.working_directory == work_dir

    def test_all_required_attributes_exist(self):
        """Test that all required attributes are properly initialized."""
        session = PersistentPythonSession()

        # Verify all attributes exist
        assert hasattr(session, "python_executable")
        assert hasattr(session, "startup_code")
        assert hasattr(session, "working_directory")
        assert hasattr(session, "process")
        assert hasattr(session, "_output_thread")
        assert hasattr(session, "_error_thread")
        assert hasattr(session, "_output_queue")
        assert hasattr(session, "_error_queue")
        assert hasattr(session, "_is_running")
        assert hasattr(session, "_execution_lock")
        assert hasattr(session, "metadata")

        # Verify queue types
        assert isinstance(session._output_queue, queue.Queue)
        assert isinstance(session._error_queue, queue.Queue)


class TestPersistentPythonSessionBasicOperations:
    """Test suite for basic PersistentPythonSession operations.

    Tests basic operations that don't require actual subprocess execution.
    """

    def test_is_running_initial_state(self):
        """Test that is_running() returns False for new session."""
        session = PersistentPythonSession()
        assert not session.is_running()

    def test_stop_when_not_running(self):
        """Test that stop() returns error when session is not running."""
        session = PersistentPythonSession()

        result = session.stop()

        assert not result["success"]
        assert "not running" in result.get("error", "").lower()

    def test_execute_without_starting(self):
        """Test that execute() returns error when session is not running."""
        session = PersistentPythonSession()

        result = session.execute("x = 1")

        assert not result["success"]
        assert "not running" in result.get("error", "").lower()

    def test_execute_result_structure(self):
        """Test that execute() returns properly structured result dict."""
        session = PersistentPythonSession()

        result = session.execute("x = 1")

        assert isinstance(result, dict)
        assert "success" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "error" in result


class TestPersistentPythonSessionMetadata:
    """Test suite for metadata handling in PersistentPythonSession.

    Tests that metadata can be stored and retrieved correctly.
    """

    def test_metadata_initialization(self):
        """Test that metadata is initialized as empty dict."""
        session = PersistentPythonSession()
        assert session.metadata == {}
        assert isinstance(session.metadata, dict)

    def test_metadata_modification(self):
        """Test that metadata can be modified and retrieved."""
        session = PersistentPythonSession()

        session.metadata["key1"] = "value1"
        session.metadata["key2"] = {"nested": "value"}

        assert session.metadata["key1"] == "value1"
        assert session.metadata["key2"]["nested"] == "value"

    def test_metadata_isolation(self):
        """Test that metadata is isolated between different session instances."""
        session1 = PersistentPythonSession()
        session2 = PersistentPythonSession()

        session1.metadata["key"] = "session1"

        assert "key" not in session2.metadata


class TestPersistentPythonSessionInternalMethods:
    """Test suite for internal methods of PersistentPythonSession.

    Tests internal helper methods used by the session.
    """

    def test_drain_queues(self):
        """Test that _drain_queues successfully clears pending output."""
        session = PersistentPythonSession()

        # Add items to output queue
        session._output_queue.put("line1")
        session._output_queue.put("line2")

        # Drain should remove items
        session._drain_queues(timeout=0.5)

        # Queue should be empty
        try:
            session._output_queue.get_nowait()
            empty = False
        except queue.Empty:
            empty = True

        assert empty

    def test_read_stream_callable(self):
        """Test that _read_stream method exists and is callable."""
        session = PersistentPythonSession()
        assert callable(session._read_stream)

    def test_execution_lock_exists(self):
        """Test that execution lock is initialized for thread safety."""
        session = PersistentPythonSession()

        assert hasattr(session, "_execution_lock")
        assert session._execution_lock is not None

    def test_lock_can_be_acquired(self):
        """Test that execution lock can be acquired and released."""
        session = PersistentPythonSession()

        # Verify the lock can be acquired
        acquired = session._execution_lock.acquire(blocking=False)
        if acquired:
            session._execution_lock.release()
            assert True
        else:
            assert False, "Lock could not be acquired"


class TestPersistentPythonSessionContextManager:
    """Test suite for context manager functionality.

    Tests that PersistentPythonSession works correctly as a context manager.
    """

    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = PersistentPythonSession(working_directory=tmpdir)

            with session:
                # Session should be running or attempting to run
                pass

            # After exiting context, session should be stopped
            assert not session.is_running()


class TestPersistentPythonSessionErrorHandling:
    """Test suite for error handling scenarios.

    Tests various error conditions and edge cases.
    """

    def test_invalid_python_executable(self):
        """Test that start() fails gracefully with invalid Python executable."""
        session = PersistentPythonSession(python_executable="/nonexistent/python")

        result = session.start()

        assert not result["success"]
        assert "not found" in result.get("error", "").lower()

    def test_restart_when_not_running(self):
        """Test that restart() works even when session is not running."""
        session = PersistentPythonSession()

        result = session.restart()

        # Should contain proper structure
        assert "success" in result
        assert "error" in result or "message" in result


# ============================================================================
# PersistentPythonSession Integration Tests
# ============================================================================


@pytest.mark.integration
class TestPersistentPythonSessionIntegration:
    """Integration test suite for PersistentPythonSession with actual subprocess execution.

    These tests use real Python subprocesses to verify end-to-end functionality.
    They are marked with @pytest.mark.integration and may take longer to run.
    """

    def test_start_and_stop(self):
        """Test starting and stopping a real Python session."""
        session = PersistentPythonSession()

        # Start session
        result = session.start()
        assert result["success"], f"Failed to start: {result.get('error')}"
        assert session.is_running()

        # Stop session
        result = session.stop()
        assert result["success"], f"Failed to stop: {result.get('error')}"
        assert not session.is_running()

    def test_execute_empty_code(self):
        """Test executing an empty Python code snippet in session."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute simple assignment
            result = session.execute("")
            assert result["success"], f"Execution failed: {result.get('error')}"
            assert isinstance(result["stdout"], str)
        finally:
            session.stop()

    def test_execute_simple_code(self):
        """Test executing simple Python code in session."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute simple assignment
            result = session.execute("x = 42")
            assert result["success"], f"Execution failed: {result.get('error')}"
            assert isinstance(result["stdout"], str)
        finally:
            session.stop()

    def test_execute_with_output(self):
        """Test executing code that produces stdout output."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute code that prints
            result = session.execute("print('hello world')")
            assert result["success"], f"Execution failed: {result.get('error')}"
            assert "hello world" in result["stdout"]
        finally:
            session.stop()

    def test_execute_single_line_for_loop(self):
        """Reproduce issue #213: a single-line loop must execute without syntax errors."""
        session = PersistentPythonSession(python_executable=sys.executable)

        try:
            started = session.start()
            assert started["success"], started

            baseline = session.execute("print('baseline')")
            assert baseline["success"], baseline
            assert baseline["stdout"].strip() == "baseline", baseline

            result = session.execute("for value in [1, 2]: print(value)")
            assert result["success"], result
            assert result["stdout"].splitlines() == ["1", "2"], result
        finally:
            session.stop()

    def test_timeout_preserves_state_and_response_alignment(self):
        """A timed-out request remains collectable and cannot become the next result."""
        with PersistentPythonSession() as session:
            result = session.execute(
                "import time; time.sleep(0.2); x = 42; print('late')", timeout=0.01
            )
            assert not result["success"], result
            assert "timed out" in result["error"], result

            rejected = session.execute("x = -1; print('wrong')")
            assert not rejected["success"], rejected
            assert "pending" in rejected["error"], rejected

            result = session.wait_for_result(timeout=5)
            assert result["success"], result
            assert result["stdout"] == "late\n"

            result = session.execute("print(x)")
            assert result["success"], result
            assert result["stdout"] == "42\n"

    def test_captures_descriptor_and_subprocess_output(self):
        """Capture OS-level and inherited subprocess writes without protocol corruption."""
        with PersistentPythonSession() as session:
            result = session.execute(
                "import os, subprocess, sys\n"
                "os.write(1, b'native stdout\\n')\n"
                "os.write(2, b'native stderr\\n')\n"
                "subprocess.run([sys.executable, '-c', "
                "\"import sys; print('child stdout'); "
                "print('child stderr', file=sys.stderr)\"], check=True)"
            )
            assert result["success"], result
            assert result["stdout"] == f"native stdout\nchild stdout{os.linesep}"
            assert result["stderr"] == f"native stderr\nchild stderr{os.linesep}"
            assert session.execute("print('next')")["stdout"] == "next\n"

    def test_preserves_output_exactly(self):
        """Preserve Unicode, trailing spaces, partial lines, and the old marker text."""
        with PersistentPythonSession() as session:
            result = session.execute("print('\\u03b1  \\n___EXECUTION_COMPLETE___', end='')")
            assert result["success"], result
            assert result["stdout"] == "\u03b1  \n___EXECUTION_COMPLETE___"

    def test_large_output_is_one_response(self):
        """Output larger than pipe capacity must not deadlock or truncate."""
        with PersistentPythonSession() as session:
            result = session.execute("print('x' * 200000, end='')")
            assert result["success"], result
            assert result["stdout"] == "x" * 200000

    @pytest.mark.parametrize(
        "source, error",
        [
            ("raise ValueError('problem')", "ValueError"),
            ("raise SystemExit(2)", "SystemExit"),
            ("if True print('bad')", "SyntaxError"),
            ("input()", "EOFError"),
            ("if True:", "Incomplete Python source"),
        ],
    )
    def test_failed_request_does_not_break_protocol(self, source, error):
        """Failures are explicit and leave the interpreter ready for another request."""
        with PersistentPythonSession() as session:
            result = session.execute(source)
            assert not result["success"], result
            assert error in result["error"], result
            assert session.execute("print('next')")["stdout"] == "next\n"

    def test_stderr_text_does_not_determine_success(self):
        """Writing an error keyword to stderr is not an execution exception."""
        with PersistentPythonSession() as session:
            result = session.execute("import sys; print('error message', file=sys.stderr)")
            assert result["success"], result
            assert result["stderr"] == "error message\n"

    def test_worker_exit_is_reported_without_waiting_for_timeout(self):
        """Unexpected worker exit must wake the response reader and allow restart."""
        with PersistentPythonSession() as session:
            result = session.execute("import os; os._exit(1)")
            assert not result["success"], result
            assert "closed its response stream" in result["error"], result
            assert not session.is_running()
            assert session.restart()["success"]
            assert session.execute("print('restarted')")["stdout"] == "restarted\n"

    def test_working_directory_imports(self, tmp_path):
        """The worker must import modules from the configured working directory."""
        (tmp_path / "local_module.py").write_text("value = 42\n")
        with PersistentPythonSession(working_directory=str(tmp_path)) as session:
            result = session.execute("import local_module; print(local_module.value)")
            assert result["success"], result
            assert result["stdout"] == "42\n"

    def test_worker_returns_one_response_per_input_line(self):
        """Malformed inputs must not consume the next request or add protocol output."""
        import ansys.common.mcp.helpers as helpers

        worker = Path(helpers.__file__).with_name("_interactive_python.py")
        requests = [
            "not json",
            "[]",
            '{"code": 1}',
            json.dumps({"code": "print('ok')"}),
        ]
        result = subprocess.run(
            [sys.executable, "-u", str(worker)],
            input="\n".join(requests) + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=True,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        assert len(responses) == len(requests)
        assert all(not response["success"] for response in responses[:3])
        assert responses[3]["stdout"] == "ok\n"
        assert result.stderr == ""

    def test_state_persistence(self):
        """Test that session maintains state across multiple executions."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Define a variable
            result1 = session.execute("x = 100")
            assert result1["success"], f"First execution failed: {result1.get('error')}"

            # Use that variable in next execution
            result2 = session.execute("y = x + 50")
            assert result2["success"], f"Second execution failed: {result2.get('error')}"

            # Check the result
            result3 = session.execute("print(y)")
            assert result3["success"], f"Third execution failed: {result3.get('error')}"
            assert "150" in result3["stdout"]
        finally:
            session.stop()

    def test_execute_with_error(self):
        """Test executing code that produces a runtime error is properly caught."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute code that raises an error
            result = session.execute("1/0")
            assert not result["success"], "Error should be caught"
            assert result["stderr"], "stderr should contain error info"
            assert "error" in result["stderr"].lower() or "exception" in result["stderr"].lower()
        finally:
            session.stop()

    def test_execute_with_syntax_error(self):
        """Test executing code with syntax error is properly caught."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute code with syntax error
            result = session.execute("if True print('bad syntax')")
            assert not result["success"], "Syntax error should be caught"
            assert result["stderr"], "stderr should contain error info"
        finally:
            session.stop()

    def test_execute_multiline_with_error(self):
        """Test executing multiline code where error occurs mid-execution."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """
x = 10
y = 20
z = x / 0
print('hello')
"""
            result = session.execute(code)
            assert not result["success"], "Error should be caught"
            assert "ZeroDivisionError" in result["stderr"] or "division by zero" in result["stderr"]
        finally:
            session.stop()

    def test_execute_with_error_no_primary_prompt(self):
        """Test runtime error is properly reported without the primary prompt."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute code that raises an error
            result = session.execute("print(1)\nprint(2)\nprint(3)\nif True print(i)")
            assert not result["success"], "Error should be caught"
            assert result["stderr"], "stderr should contain error info"
            assert "error" in result["stderr"].lower() or "exception" in result["stderr"].lower()
            assert ">>>" not in result["stderr"]
        finally:
            session.stop()

    def test_execute_with_error_no_secondary_prompt(self):
        """Test runtime error is properly reported without the secondary prompt."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute code that raises an error
            result = session.execute("for i in range(1, 5):\n   if True print(i)")
            assert not result["success"], "Error should be caught"
            assert result["stderr"], "stderr should contain error info"
            assert "error" in result["stderr"].lower() or "exception" in result["stderr"].lower()
            assert "..." not in result["stderr"]
        finally:
            session.stop()

    def test_with_startup_code(self):
        """Test session with startup code that runs on initialization."""
        startup_code = "import math\nPI = 3.14159"
        session = PersistentPythonSession(startup_code=startup_code)

        try:
            result = session.start()
            assert result["success"], f"Failed to start: {result.get('error')}"

            # Verify startup code was executed
            check_result = session.execute("print(PI)")
            assert check_result["success"], f"Execution failed: {check_result.get('error')}"
            assert "3.14159" in check_result["stdout"]
        finally:
            session.stop()

    def test_context_manager_with_execution(self):
        """Test session usage as a context manager with code execution."""
        with PersistentPythonSession() as session:
            assert session.is_running()

            result = session.execute("print('context manager test')")
            assert result["success"], f"Execution failed: {result.get('error')}"
            assert "context manager test" in result["stdout"]

        # After exiting context, session should be stopped
        assert not session.is_running()

    def test_restart_functionality(self):
        """Test restarting a session clears state and re-runs startup code."""
        session = PersistentPythonSession(startup_code="x = 10")

        try:
            # Start and verify startup code ran
            session.start()
            result1 = session.execute("print(x)")
            assert result1["success"], f"First execution failed: {result1.get('error')}"
            assert "10" in result1["stdout"]

            # Modify the variable
            session.execute("x = 999")

            # Verify modification
            result1 = session.execute("print(x)")
            assert result1["success"], f"First execution failed: {result1.get('error')}"
            assert "999" in result1["stdout"]

            # Restart session
            restart_result = session.restart()
            assert restart_result["success"], f"Restart failed: {restart_result.get('error')}"
            assert session.is_running()

            # Startup code should have run again, resetting x to 10
            result2 = session.execute("print(x)")
            assert result2["success"], f"Second execution failed: {result2.get('error')}"
            assert "10" in result2["stdout"]
        finally:
            if session.is_running():
                session.stop()

    def test_multiple_sequential_executions(self):
        """Test running multiple commands sequentially in the same session."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Run multiple commands
            for i in range(5):
                result = session.execute(f"print({i})")
                assert result["success"], f"Execution {i} failed: {result.get('error')}"
                assert str(i) in result["stdout"]
        finally:
            session.stop()

    def test_with_one_indented_code_block(self):
        """Test running code with an indented block."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """\
for i in range(1,5):
    print(i)
print('done')
"""
            result = session.execute(code)

            assert result["success"], f"Execution failed: {result.get('error')}"

            expected_result = """\
1
2
3
4
done"""
            assert expected_result in result["stdout"]
        finally:
            session.stop()

    def test_ending_with_one_indented_code_block(self):
        """Test running code with an indented block."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """\
for n in range(1, 5):
    if n % 2 == 0:
        continue
    print(n)"""
            result = session.execute(code)

            assert result["success"], f"Execution failed: {result.get('error')}"

            expected_result = """\
1
3"""
            assert expected_result in result["stdout"]
        finally:
            session.stop()

    def test_with_nested_indented_code_blocks(self):
        """Test running code with multiple nested and indented blocks."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """\
for i in range(1,5):
    if i > 3:
        print(i)
    else:
        for j in range(1, i):
            print(j)
print('done')
"""
            result = session.execute(code)

            assert result["success"], f"Execution failed: {result.get('error')}"

            expected_result = """\
1
1
2
4
done"""
            assert expected_result in result["stdout"]
        finally:
            session.stop()

    def test_with_blank_lines_in_indented_blocks(self):
        """Test running code with multiple nested blocks that include blank lines."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """\
for i in range(1,5):
    if i > 3:

        print(i)

    else:
        for j in range(1, i):

            print(j)
print('done')
"""
            result = session.execute(code)

            assert result["success"], f"Execution failed: {result.get('error')}"

            expected_result = """\
1
1
2
4
done"""
            assert expected_result in result["stdout"]
        finally:
            session.stop()

    def test_ending_with_deep_nested_code_blocks(self):
        """Test running code ending on a deeply indented section."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """\
for i in range(1,5):
    if i % 2 == 0:
        if i > 1:
            if i == 2:
                print(2)
"""
            result = session.execute(code)

            assert result["success"], f"Execution failed: {result.get('error')}"

            expected_result = "2"
            assert expected_result in result["stdout"]
        finally:
            session.stop()

    def test_repeated_indented_code_blocks(self):
        """Test running code with an indented block."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """\
for n in range(1, 5):
    if n % 2 == 0:
        continue
    print(n)
for n in range(1, 5):
    if n % 2 == 0:
        if n % 2 == 0:
            if n % 2 == 0:
                if n % 2 == 0:
                    continue
    print(2*n)


for n in range(1, 5):
    if n % 2 == 0:

        continue

    print(3*n)
for n in range(1, 5):
    if n % 2 == 0:
        continue
    print(4*n)"""

            result = session.execute(code)

            assert result["success"], f"Execution failed: {result.get('error')}"

            expected_result = """\
1
3
2
6
3
9
4
12"""
            assert expected_result in result["stdout"]
        finally:
            session.stop()

    def test_indented_code_blocks_with_continuations(self):
        """Test running code with indented blocks containing else|elif|except|finally."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """\
n = 5
score = 85

if n % 2 == 0:
    print(f"{n} is even")
else:
    print(f"{n} is odd")
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Error: divide by zero!")
finally:
    print("finally")
if score >= 90:
    print("Grade: A")
elif score >= 80:
    print("Grade: B")
elif score >= 70:
    print("Grade: C")
else:
    print("Grade: F")"""

            result = session.execute(code)

            assert result["success"], f"Execution failed: {result.get('error')}"

            expected_result = """\
5 is odd
Error: divide by zero!
finally
Grade: B"""
            assert expected_result in result["stdout"]
        finally:
            session.stop()

    def test_metadata_persistence_across_executions(self):
        """Test that metadata persists across code executions."""
        session = PersistentPythonSession()
        session.metadata["test_key"] = "test_value"

        try:
            session.start()
            result = session.execute("x = 1")
            assert result["success"], f"Execution failed: {result.get('error')}"

            # Metadata should still be accessible
            assert session.metadata["test_key"] == "test_value"
        finally:
            session.stop()

    def test_stderr_collection(self):
        """Test that stdout and stderr are returned in the same response."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Execute code that writes to stderr after printing
            code = """
import sys
print('stdout message')
sys.stderr.write('stderr message\\n')
"""
            result = session.execute(code)
            assert result["success"], f"Execution failed: {result.get('error')}"
            assert "stdout message" in result["stdout"]
            assert "stderr message" in result["stderr"]
        finally:
            session.stop()

    def test_execute_with_warning(self):
        """Test that Python warnings are captured in stderr."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Generate a deprecation warning
            code = """
import warnings
warnings.warn('This is a test warning', DeprecationWarning)
print('done')
"""
            result = session.execute(code)
            # Warnings go to stderr but shouldn't fail execution
            assert "done" in result["stdout"]
        finally:
            session.stop()

    def test_silent_execution_waits_for_completion(self):
        """Silence longer than the former idle timeout must not truncate execution."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """
import time
time.sleep(1.4)
print('done')
"""
            result = session.execute(code)

            assert result["success"], result
            assert result["stdout"] == "done\n"

        finally:
            session.stop()

    def test_no_output_timeout_can_be_disabled(self):
        """Test that setting no_output_timeout=None disables the idle check."""
        session = PersistentPythonSession()

        try:
            session.start()

            # Sleeps briefly, but longer than the default 1.2s idle timeout
            code = """
import time
time.sleep(1.4)
print('done')
"""
            # no_output_timeout=None disables the check; rely on the outer timeout instead
            result = session.execute(code, no_output_timeout=None)

            assert "done" in result["stdout"]

        finally:
            session.stop()

    def test_no_output_timeout_custom_value(self):
        """The deprecated idle timeout must not terminate collection of a JSON response."""
        session = PersistentPythonSession()

        try:
            session.start()

            code = """
import time
time.sleep(1)
print('done')
"""
            result = session.execute(code, no_output_timeout=0.5)

            assert result["success"], result
            assert result["stdout"] == "done\n"

        finally:
            session.stop()

    def test_no_output_timeout_invalid_values(self):
        """Test that invalid no_output_timeout values raise ValueError."""
        session = PersistentPythonSession()
        session.start()

        try:
            for bad_value in (0, -1, float("nan"), float("-inf"), "5"):
                with pytest.raises(ValueError, match="no_output_timeout"):
                    session.execute("print('hi')", no_output_timeout=bad_value)
        finally:
            session.stop()
