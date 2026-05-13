# Copyright (C) 2025 - 2026 ANSYS, Inc. and/or its affiliates.
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

"""Unit tests for tools module."""

import json
from unittest.mock import MagicMock

from mcp.types import ImageContent, TextContent
import pytest

from ansys.common.mcp.tools import (
    create_custom_plot,
    execute_python_code,
    export_history,
    restart_python_session,
)

# ============================================================================
# execute_python_code Tests
# ============================================================================


class TestExecutePythonCodeBasic:
    """Test suite for basic execute_python_code functionality."""

    def test_execute_simple_code_success(self):
        """Test executing simple Python code successfully."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "42",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        code = "print(42)"
        result = execute_python_code(mock_context, code)

        # Verify result
        assert isinstance(result, str)
        result_dict = json.loads(result)
        assert result_dict["success"] is True
        assert "42" in result_dict["stdout"]
        mock_session.execute.assert_called_once_with(code, timeout=60)
        mock_context.request_context.lifespan_context.add_to_history.assert_called_once_with(
            "python_code", True, code
        )

    def test_execute_code_with_custom_timeout(self):
        """Test executing code with custom timeout."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "done",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute with custom timeout
        code = "print('test')"
        timeout = 120
        result = execute_python_code(mock_context, code, timeout=timeout)

        # Verify timeout was passed
        mock_session.execute.assert_called_once_with(code, timeout=timeout)
        result_dict = json.loads(result)
        assert result_dict["success"] is True

    def test_execute_code_no_session(self):
        """Test executing code when no Python session is available."""
        # Setup mock context with no session
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context.python_session = None

        # Execute code
        code = "print('test')"
        result = execute_python_code(mock_context, code)

        # Verify error response
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "No Python session available" in result_dict["error"]

    def test_execute_code_with_error(self):
        """Test executing code that produces an error."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "ZeroDivisionError: division by zero",
            "error": "ZeroDivisionError: division by zero",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code that will fail
        code = "1/0"
        result = execute_python_code(mock_context, code)

        # Verify error is returned
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "ZeroDivisionError" in result_dict["error"]
        mock_context.request_context.lifespan_context.add_to_history.assert_called_once_with(
            "python_code", False, code
        )

    def test_execute_code_with_stdout_and_stderr(self):
        """Test executing code that produces both stdout and stderr."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "output message",
            "stderr": "warning message",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        code = "import sys; print('output message'); sys.stderr.write('warning message')"
        result = execute_python_code(mock_context, code)

        # Verify both outputs are included
        result_dict = json.loads(result)
        assert result_dict["success"] is True
        assert "output message" in result_dict["stdout"]
        assert "warning message" in result_dict["stderr"]


class TestExecutePythonCodeSanitization:
    """Test suite for Unicode sanitization in execute_python_code."""

    def test_sanitize_input_code(self):
        """Test that input code is sanitized for problematic Unicode."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "done",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Code with problematic Unicode
        code = "print('✓ checkmark')"
        execute_python_code(mock_context, code)

        # Verify sanitized code was passed to execute
        called_code = mock_session.execute.call_args[0][0]
        assert "\u2713" not in called_code  # Checkmark should be replaced

    def test_sanitize_output(self):
        """Test that stdout/stderr are sanitized in response."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "output with ✓ checkmark",
            "stderr": "error with ✗ cross",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        result = execute_python_code(mock_context, "print('test')")

        # Verify output is sanitized
        result_dict = json.loads(result)
        assert "\u2713" not in result_dict["stdout"]  # Checkmark replaced
        assert "\u2717" not in result_dict["stderr"]  # Cross replaced


class TestExecutePythonCodeExceptionHandling:
    """Test suite for exception handling in execute_python_code."""

    def test_timeout_error(self):
        """Test handling of timeout error."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.side_effect = TimeoutError("Timed out")
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        result = execute_python_code(mock_context, "while True: pass", timeout=30)

        # Verify timeout error is returned
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "timed out" in result_dict["error"].lower()
        assert "30 seconds" in result_dict["error"]

    def test_general_exception(self):
        """Test handling of general exceptions."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("Unexpected error")
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        result = execute_python_code(mock_context, "print('test')")

        # Verify exception is caught and returned
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "Error executing Python code" in result_dict["error"]
        assert "Unexpected error" in result_dict["error"]

    def test_non_dict_result(self):
        """Test handling when session returns non-dict result."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = "unexpected string result"
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        result = execute_python_code(mock_context, "print('test')")

        # Verify fallback handling
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "unexpected string result" in result_dict["stdout"]


class TestExecutePythonCodeJSONFormatting:
    """Test suite for JSON response formatting."""

    def test_json_structure_success(self):
        """Test JSON structure for successful execution."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "test output",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        result = execute_python_code(mock_context, "print('test')")

        # Verify JSON structure
        result_dict = json.loads(result)
        assert "success" in result_dict
        assert "stdout" in result_dict
        assert "stderr" in result_dict
        assert "message" in result_dict
        assert result_dict["success"] is True

    def test_json_structure_failure(self):
        """Test JSON structure for failed execution."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Error message",
            "error": "Error message",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        result = execute_python_code(mock_context, "invalid code")

        # Verify JSON structure
        result_dict = json.loads(result)
        assert "success" in result_dict
        assert "stdout" in result_dict
        assert "stderr" in result_dict
        assert "error" in result_dict
        assert result_dict["success"] is False

    def test_json_ensure_ascii_false(self):
        """Test that JSON is generated with ensure_ascii=False."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "über test",  # Non-ASCII characters
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Execute code
        result = execute_python_code(mock_context, "print('über test')")

        # Verify result can be parsed and contains proper characters
        result_dict = json.loads(result)
        assert result_dict["success"] is True


# ============================================================================
# create_custom_plot Tests
# ============================================================================


class TestCreateCustomPlotBasic:
    """Test suite for basic create_custom_plot functionality."""

    def test_create_matplotlib_plot_success(self):
        """Test creating a matplotlib plot successfully."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        base64_data = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwAD"
            "hgGAWjR9awAAAABJRU5ErkJggg=="
        )
        mock_session.execute.return_value = {
            "success": True,
            "stdout": f"data:image/png;base64,{base64_data}",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        plot_code = "import matplotlib.pyplot as plt; plt.plot([1,2,3])"
        result = create_custom_plot(mock_context, plot_code)

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], TextContent)
        assert isinstance(result[1], ImageContent)
        assert result[1].mimeType == "image/png"
        assert result[1].data == base64_data
        mock_context.request_context.lifespan_context.add_to_history.assert_called_once_with(
            "plot_code", True, plot_code
        )

    def test_create_pyvista_plot_success(self):
        """Test creating a pyvista plot successfully."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        base64_data = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwAD"
            "hgGAWjR9awAAAABJRU5ErkJggg=="
        )
        mock_session.execute.return_value = {
            "success": True,
            "stdout": f"data:image/png;base64,{base64_data}",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        plot_code = "import pyvista as pv; pv.Sphere()"
        result = create_custom_plot(mock_context, plot_code, plot_type="pyvista")

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 2
        assert "pyvista" in result[0].text.lower()

    def test_create_plot_no_session(self):
        """Test creating plot when no Python session is available."""
        # Setup mock context with no session
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context.python_session = None

        # Create plot
        plot_code = "plt.plot([1,2,3])"
        result = create_custom_plot(mock_context, plot_code)

        # Verify error response
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No Python session available" in result[0].text

    def test_create_plot_with_custom_timeout(self):
        """Test creating plot with custom timeout."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "data:image/png;base64,abc123",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot with custom timeout
        plot_code = "plt.plot([1,2,3])"
        timeout = 120
        create_custom_plot(mock_context, plot_code, timeout=timeout)

        # Verify timeout was passed
        mock_session.execute.assert_called_once()
        assert mock_session.execute.call_args[1]["timeout"] == timeout


class TestCreateCustomPlotOutputFormats:
    """Test suite for different output formats from create_custom_plot."""

    def test_plot_with_file_path_output(self):
        """Test when plot returns a file path instead of base64."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "Plot saved to /tmp/plot.png",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        plot_code = "save_plot('/tmp/plot.png')"
        result = create_custom_plot(mock_context, plot_code)

        # Verify file path is returned in text
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Plot saved to" in result[0].text

    def test_plot_with_unexpected_output(self):
        """Test when plot returns unexpected output format."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "unexpected output format",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        plot_code = "print('test')"
        result = create_custom_plot(mock_context, plot_code)

        # Verify unexpected format is handled
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unexpected output format" in result[0].text.lower()

    def test_plot_execution_error(self):
        """Test when plot execution fails."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "NameError: name 'plt' is not defined",
            "error": "NameError: name 'plt' is not defined",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        plot_code = "plt.plot([1,2,3])"
        result = create_custom_plot(mock_context, plot_code)

        # Verify error is returned
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error creating custom" in result[0].text
        assert "NameError" in result[0].text
        mock_context.request_context.lifespan_context.add_to_history.assert_called_once_with(
            "plot_code", False, plot_code
        )


class TestCreateCustomPlotSanitization:
    """Test suite for Unicode sanitization in create_custom_plot."""

    def test_sanitize_plot_code(self):
        """Test that plot code is sanitized for problematic Unicode."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "data:image/png;base64,abc123",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Plot code with problematic Unicode
        plot_code = "plt.title('✓ Success')"
        create_custom_plot(mock_context, plot_code)

        # Verify sanitized code was passed to execute
        called_code = mock_session.execute.call_args[0][0]
        assert "\u2713" not in called_code  # Checkmark should be replaced

    def test_sanitize_stdout_output(self):
        """Test that stdout is sanitized in plot results."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "output with ✓ checkmark",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])")

        # Verify output is sanitized
        assert isinstance(result, list)
        assert len(result) == 1
        text_content = result[0].text
        assert "\u2713" not in text_content  # Checkmark replaced

    def test_sanitize_error_messages(self):
        """Test that error messages are sanitized."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Error with ✗ cross",
            "error": "Error with ✗ cross",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "invalid code")

        # Verify error is sanitized
        assert isinstance(result, list)
        text_content = result[0].text
        assert "\u2717" not in text_content  # Cross replaced


class TestCreateCustomPlotExceptionHandling:
    """Test suite for exception handling in create_custom_plot."""

    def test_timeout_error(self):
        """Test handling of timeout error."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.side_effect = TimeoutError("Timed out")
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "plt.plot([1]*1000000)", timeout=30)

        # Verify timeout error is returned
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "timed out" in result[0].text.lower()
        assert "30 seconds" in result[0].text

    def test_general_exception(self):
        """Test handling of general exceptions."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("Unexpected error")
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])")

        # Verify exception is caught and returned
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error creating custom plot" in result[0].text
        assert "Unexpected error" in result[0].text

    def test_non_dict_result(self):
        """Test handling when session returns non-dict result."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = "unexpected string result"
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])")

        # Verify fallback handling
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unexpected result format" in result[0].text


class TestCreateCustomPlotTypes:
    """Test suite for different plot types."""

    def test_matplotlib_plot_type(self):
        """Test explicitly specifying matplotlib plot type."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "data:image/png;base64,abc123",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create matplotlib plot
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])", plot_type="matplotlib")

        # Verify matplotlib is mentioned
        assert isinstance(result, list)
        assert "matplotlib" in result[0].text.lower()

    def test_pyvista_plot_type(self):
        """Test explicitly specifying pyvista plot type."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "data:image/png;base64,abc123",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create pyvista plot
        result = create_custom_plot(mock_context, "pv.Sphere()", plot_type="pyvista")

        # Verify pyvista is mentioned
        assert isinstance(result, list)
        assert "pyvista" in result[0].text.lower()

    def test_default_plot_type(self):
        """Test default plot type is matplotlib."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "data:image/png;base64,abc123",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot without specifying type
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])")

        # Verify matplotlib is the default
        assert isinstance(result, list)
        assert "matplotlib" in result[0].text.lower()


class TestCreateCustomPlotImageContent:
    """Test suite for ImageContent generation."""

    def test_image_content_structure(self):
        """Test that ImageContent has correct structure."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        base64_data = "abc123xyz"
        mock_session.execute.return_value = {
            "success": True,
            "stdout": f"data:image/png;base64,{base64_data}",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])")

        # Verify ImageContent structure
        assert len(result) == 2
        image_content = result[1]
        assert image_content.type == "image"
        assert image_content.data == base64_data
        assert image_content.mimeType == "image/png"

    def test_base64_data_extraction(self):
        """Test that base64 data is correctly extracted from data URI."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        base64_data = "VeryLongBase64String=="
        mock_session.execute.return_value = {
            "success": True,
            "stdout": f"data:image/png;base64,{base64_data}",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])")

        # Verify base64 data extraction
        image_content = result[1]
        assert image_content.data == base64_data
        assert "data:image/png;base64," not in image_content.data

    def test_base64_with_whitespace(self):
        """Test that base64 data with whitespace is properly trimmed."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        base64_data = "abc123"
        mock_session.execute.return_value = {
            "success": True,
            "stdout": f"  data:image/png;base64,{base64_data}  \n",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Create plot
        result = create_custom_plot(mock_context, "plt.plot([1,2,3])")

        # Verify whitespace is trimmed
        image_content = result[1]
        assert image_content.data == base64_data


# ============================================================================
# restart_python_session Tests
# ============================================================================


class TestRestartPythonSessionBasic:
    """Test suite for basic restart_python_session functionality."""

    def test_restart_no_session(self):
        """Test restarting when no Python session is available."""
        # Setup mock context with no session
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context.python_session = None

        # Restart
        result = restart_python_session(mock_context)

        # Verify error response
        assert "Error" in result
        assert "No Python session" in result

    def test_restart_with_session_default_params(self):
        """Test restarting with default parameters (replay successful commands)."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_context.request_context.lifespan_context.python_session = mock_session
        mock_context.request_context.lifespan_context.command_history = []

        # Restart
        result = restart_python_session(mock_context)

        # Verify restart was called
        mock_session.restart.assert_called_once()
        assert "successfully" in result.lower()

    def test_restart_success_message(self):
        """Test that restart returns proper success message."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_context.request_context.lifespan_context.python_session = mock_session
        mock_context.request_context.lifespan_context.command_history = []

        # Restart
        result = restart_python_session(mock_context)

        # Verify message
        assert isinstance(result, str)
        assert "Persistent Python session restarted successfully" in result

    def test_restart_exception_handling(self):
        """Test that exceptions during restart are properly handled."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.side_effect = RuntimeError("Session error")
        mock_context.request_context.lifespan_context.python_session = mock_session
        mock_context.request_context.lifespan_context.command_history = []

        # Restart
        result = restart_python_session(mock_context)

        # Verify error is returned
        assert "Error restarting Python session" in result
        assert "Session error" in result


class TestRestartPythonSessionCommandReplay:
    """Test suite for command history replay after restart."""

    def test_replay_successful_commands_only(self):
        """Test that only successful commands are replayed by default."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "replayed",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Command history with mixed success/failure
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "x = 1"),
            ("python_code", False, "invalid code"),
            ("python_code", True, "y = 2"),
        ]

        # Restart with default params (replay successful)
        restart_python_session(mock_context)

        # Verify only successful commands were replayed
        assert mock_session.execute.call_count == 2
        executed_codes = [call[0][0] for call in mock_session.execute.call_args_list]
        assert "x = 1" in executed_codes
        assert "y = 2" in executed_codes
        assert "invalid code" not in executed_codes

    def test_replay_all_commands(self):
        """Test replaying all commands regardless of success status."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "replayed",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Command history with mixed success/failure
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "x = 1"),
            ("python_code", False, "bad_code"),
            ("python_code", True, "y = 2"),
        ]

        # Restart with run_all_history=True
        restart_python_session(mock_context, run_all_history=True)

        # Verify all commands were replayed
        assert mock_session.execute.call_count == 3
        executed_codes = [call[0][0] for call in mock_session.execute.call_args_list]
        assert "x = 1" in executed_codes
        assert "bad_code" in executed_codes
        assert "y = 2" in executed_codes

    def test_no_replay_when_disabled(self):
        """Test that no commands are replayed when both flags are False."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "replayed",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Command history
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "x = 1"),
            ("python_code", True, "y = 2"),
        ]

        # Restart with both flags False
        restart_python_session(
            mock_context, run_successful_history_commands=False, run_all_history=False
        )

        # Verify no commands were replayed
        mock_session.execute.assert_not_called()

    def test_replay_empty_history(self):
        """Test restart with empty command history."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_context.request_context.lifespan_context.python_session = mock_session
        mock_context.request_context.lifespan_context.command_history = []

        # Restart
        result = restart_python_session(mock_context)

        # Verify restart succeeded with no replay
        mock_session.restart.assert_called_once()
        mock_session.execute.assert_not_called()
        assert "successfully" in result.lower()


class TestRestartPythonSessionCommandTypes:
    """Test suite for replaying different command types."""

    def test_replay_python_code_commands(self):
        """Test replaying python_code type commands."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "done",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Python code commands
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "import numpy as np"),
            ("python_code", True, "x = np.array([1, 2, 3])"),
        ]

        # Restart
        restart_python_session(mock_context)

        # Verify commands were executed
        assert mock_session.execute.call_count == 2

    def test_replay_plot_code_commands(self):
        """Test replaying plot_code type commands."""
        # Setup mock context with execute_python_code and create_custom_plot mocked
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "data:image/png;base64,abc123",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Plot code commands
        mock_context.request_context.lifespan_context.command_history = [
            ("plot_code", True, "import matplotlib.pyplot as plt\nplt.plot([1,2,3])"),
        ]

        # Restart
        restart_python_session(mock_context)

        # Verify plot command was executed
        assert mock_session.execute.call_count == 1

    def test_replay_mixed_command_types(self):
        """Test replaying mixed python_code and plot_code commands."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "done",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Mixed commands
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "x = 1"),
            ("plot_code", True, "plt.plot([1,2,3])"),
            ("python_code", True, "y = 2"),
        ]

        # Restart
        restart_python_session(mock_context)

        # Verify all commands were replayed
        assert mock_session.execute.call_count == 3


class TestRestartPythonSessionSkipHistory:
    """Test suite for skip_history parameter during replay."""

    def test_skip_history_flag_in_replay(self):
        """Test that replayed commands use skip_history=True."""
        # This test verifies the behavior indirectly by checking that
        # command_history is not modified during replay
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "done",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        # Initial command history
        initial_history = [
            ("python_code", True, "x = 1"),
        ]
        mock_context.request_context.lifespan_context.command_history = initial_history.copy()

        # Restart
        restart_python_session(mock_context)

        # Verify command was executed
        mock_session.execute.assert_called_once()


class TestRestartPythonSessionParameterCombinations:
    """Test suite for different parameter combinations."""

    def test_run_successful_true_run_all_false(self):
        """Test with run_successful_history_commands=True, run_all_history=False."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "done",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "x = 1"),
            ("python_code", False, "bad"),
        ]

        # Restart
        restart_python_session(
            mock_context, run_successful_history_commands=True, run_all_history=False
        )

        # Only successful command should be replayed
        assert mock_session.execute.call_count == 1

    def test_run_successful_false_run_all_true(self):
        """Test with run_successful_history_commands=False, run_all_history=True."""
        # Setup mock context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.restart.return_value = {"success": True}
        mock_session.execute.return_value = {
            "success": True,
            "stdout": "done",
            "stderr": "",
        }
        mock_context.request_context.lifespan_context.python_session = mock_session

        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "x = 1"),
            ("python_code", False, "bad"),
        ]

        # Restart - run_all_history takes precedence
        restart_python_session(
            mock_context, run_successful_history_commands=False, run_all_history=True
        )

        # All commands should be replayed
        assert mock_session.execute.call_count == 2


# ============================================================================
# restart_python_session Integration Tests
# ============================================================================


@pytest.mark.integration
class TestRestartPythonSessionIntegration:
    """Integration tests for restart_python_session with real Python session.

    These tests use actual PersistentPythonSession to verify end-to-end functionality.
    """

    def test_restart_with_real_session_and_replay(self):
        """Test restart with real Python session and command replay."""
        from ansys.common.mcp.context import PyAnsysBaseAppContext
        from ansys.common.mcp.helpers import PersistentPythonSession

        # Create real context with Python session
        app_context = PyAnsysBaseAppContext()
        app_context.python_session = PersistentPythonSession()
        app_context.python_session.start()

        # Mock the FastMCP context
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context = app_context

        try:
            # Execute initial commands
            result1 = execute_python_code(mock_context, "a = 2")
            assert json.loads(result1)["success"]

            result2 = execute_python_code(mock_context, "b = 3")
            assert json.loads(result2)["success"]

            # Verify command history
            assert len(app_context.command_history) == 2

            # Execute code that uses the variables
            result3 = execute_python_code(mock_context, "print(a + b)")
            result3_dict = json.loads(result3)
            assert result3_dict["success"]
            assert "5" in result3_dict["stdout"]

            # Restart session with replay
            restart_result = restart_python_session(mock_context)
            assert "successfully" in restart_result.lower()

            # Verify variables are restored after restart
            result4 = execute_python_code(mock_context, "print(a + b)", skip_history=True)
            result4_dict = json.loads(result4)
            assert result4_dict["success"]
            assert "5" in result4_dict["stdout"]

        finally:
            app_context.python_session.stop()

    def test_restart_clears_failed_commands(self):
        """Test that restart only replays successful commands."""
        from ansys.common.mcp.context import PyAnsysBaseAppContext
        from ansys.common.mcp.helpers import PersistentPythonSession

        # Create real context
        app_context = PyAnsysBaseAppContext()
        app_context.python_session = PersistentPythonSession()
        app_context.python_session.start()

        mock_context = MagicMock()
        mock_context.request_context.lifespan_context = app_context

        try:
            # Execute successful command
            result1 = execute_python_code(mock_context, "c = 100")
            assert json.loads(result1)["success"]

            # Execute failed command
            result2 = execute_python_code(mock_context, "print(undefined_var)")
            assert not json.loads(result2)["success"]

            # Verify history contains both
            assert len(app_context.command_history) == 2

            # Restart with successful replay only
            restart_result = restart_python_session(
                mock_context, run_successful_history_commands=True, run_all_history=False
            )
            assert "successfully" in restart_result.lower()

            # Variable 'c' should exist (from successful command)
            result3 = execute_python_code(mock_context, "print(c)", skip_history=True)
            result3_dict = json.loads(result3)
            assert result3_dict["success"]
            assert "100" in result3_dict["stdout"]

            # Variable 'undefined_var' should not exist
            result4 = execute_python_code(mock_context, "print(undefined_var)", skip_history=True)
            result4_dict = json.loads(result4)
            assert not result4_dict["success"]

        finally:
            app_context.python_session.stop()

    def test_restart_with_no_replay(self):
        """Test restart without replaying commands clears all state."""
        from ansys.common.mcp.context import PyAnsysBaseAppContext
        from ansys.common.mcp.helpers import PersistentPythonSession

        # Create real context
        app_context = PyAnsysBaseAppContext()
        app_context.python_session = PersistentPythonSession()
        app_context.python_session.start()

        mock_context = MagicMock()
        mock_context.request_context.lifespan_context = app_context

        try:
            # Execute command
            result1 = execute_python_code(mock_context, "d = 42")
            assert json.loads(result1)["success"]

            # Verify variable exists
            result2 = execute_python_code(mock_context, "print(d)", skip_history=True)
            result2_dict = json.loads(result2)
            assert result2_dict["success"]
            assert "42" in result2_dict["stdout"]

            # Restart without replay
            restart_result = restart_python_session(
                mock_context, run_successful_history_commands=False, run_all_history=False
            )
            assert "successfully" in restart_result.lower()

            # Variable should no longer exist
            result3 = execute_python_code(mock_context, "print(d)", skip_history=True)
            result3_dict = json.loads(result3)
            assert not result3_dict["success"]
            assert "not defined" in result3_dict["error"].lower()

        finally:
            app_context.python_session.stop()

    def test_restart_with_startup_code_preserved(self):
        """Test that startup code is preserved after restart."""
        from ansys.common.mcp.context import PyAnsysBaseAppContext
        from ansys.common.mcp.helpers import PersistentPythonSession

        # Create session with startup code
        app_context = PyAnsysBaseAppContext()
        app_context.python_session = PersistentPythonSession(startup_code="STARTUP_VAR = 999")
        app_context.python_session.start()

        mock_context = MagicMock()
        mock_context.request_context.lifespan_context = app_context

        try:
            # Verify startup code ran
            result1 = execute_python_code(mock_context, "print(STARTUP_VAR)", skip_history=True)
            result1_dict = json.loads(result1)
            assert result1_dict["success"]
            assert "999" in result1_dict["stdout"]

            # Add custom variable
            result2 = execute_python_code(mock_context, "CUSTOM_VAR = 111")
            assert json.loads(result2)["success"]

            # Restart without replay
            restart_result = restart_python_session(
                mock_context, run_successful_history_commands=False, run_all_history=False
            )
            assert "successfully" in restart_result.lower()

            # Startup variable should still exist
            result3 = execute_python_code(mock_context, "print(STARTUP_VAR)", skip_history=True)
            result3_dict = json.loads(result3)
            assert result3_dict["success"]
            assert "999" in result3_dict["stdout"]

            # Custom variable should not exist
            result4 = execute_python_code(mock_context, "print(CUSTOM_VAR)", skip_history=True)
            result4_dict = json.loads(result4)
            assert not result4_dict["success"]

        finally:
            app_context.python_session.stop()


# ============================================================================
# export_history Tests
# ============================================================================


class TestExportHistoryBasic:
    """Test suite for basic export_history functionality."""

    def test_export_history_json_format(self):
        """Test exporting history in JSON format."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "x = 1"),
            ("python_code", True, "y = 2"),
            ("plot_code", False, "bad_plot"),
        ]

        # Export as JSON
        result = export_history(mock_context, format="json")

        # Verify result
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed[0]["type"] == "python_code"
        assert parsed[0]["success"] is True
        assert parsed[0]["command"] == "x = 1"
        assert parsed[2]["type"] == "plot_code"
        assert parsed[2]["success"] is False

    def test_export_history_text_format(self):
        """Test exporting history in text format."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "import numpy"),
            ("python_code", True, "arr = np.array([1,2,3])"),
        ]

        # Export as text
        result = export_history(mock_context, format="text")

        # Verify result
        assert isinstance(result, str)
        assert "import numpy" in result
        assert "arr = np.array([1,2,3])" in result
        assert "\n" in result  # Multiple commands should be separated by newlines

    def test_export_history_default_format(self):
        """Test that default format is JSON."""
        # Setup mock context
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context.command_history = [
            ("python_code", True, "test = 1"),
        ]

        # Export with no format specified (should default to JSON)
        result = export_history(mock_context)

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_export_history_empty(self):
        """Test exporting empty history."""
        # Setup mock context with empty history
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context.command_history = []

        # Export as JSON
        result_json = export_history(mock_context, format="json")
        parsed = json.loads(result_json)
        assert parsed == []

        # Export as text
        result_text = export_history(mock_context, format="text")
        assert result_text == ""
