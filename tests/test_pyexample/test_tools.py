# Copyright (C) 2025 - 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Tests for PyExample MCP tools.

These tests validate the MCP tool implementations and their interaction
with the PyExample instance and context.
"""

import json
from unittest.mock import MagicMock

from pyexample_mcp import PyExampleContext
from pyexample_mcp.mock_pyexample import PyExample
from pyexample_mcp.tools import (
    create_model,
    execute_command,
    execute_python_code,
    get_command_history,
    run_simulation,
)
import pytest


@pytest.fixture
def app_context():
    """Fixture providing a mock context with PyExample instance."""
    context = PyExampleContext(
        python_session=MagicMock(),
        command_history=[],
    )
    context.example_instance = PyExample()
    return context


@pytest.fixture
def mock_fastmcp_context(app_context):
    """Fixture providing a mock FastMCP context."""
    context = MagicMock()
    context.request_context = MagicMock()
    context.fastmcp._lifespan_result = app_context
    return context


class TestExecuteCommandTool:
    """Tests for the execute_command tool."""

    def test_execute_command_success(self, mock_fastmcp_context):
        """Test successful command execution."""
        result = execute_command(ctx=mock_fastmcp_context, command="CREATE MODEL test")

        assert "created successfully" in result
        assert "test" in result

    def test_execute_command_updates_history(self, mock_fastmcp_context):
        """Test that commands are added to history."""
        execute_command(ctx=mock_fastmcp_context, command="CREATE MODEL test1")
        execute_command(ctx=mock_fastmcp_context, command="CREATE MODEL test2")

        context = mock_fastmcp_context.fastmcp._lifespan_result
        assert len(context.command_history) == 2
        assert "CREATE MODEL test1" in context.command_history
        assert "CREATE MODEL test2" in context.command_history

    def test_execute_command_no_connection(self, mock_fastmcp_context):
        """Test execute_command when PyExample not connected."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.example_instance = None

        result = execute_command(ctx=mock_fastmcp_context, command="STATUS")

        assert "Error: PyExample not connected" in result


class TestCreateModelTool:
    """Tests for the create_model tool."""

    def test_create_model_basic(self, mock_fastmcp_context):
        """Test basic model creation."""
        result = create_model(ctx=mock_fastmcp_context, name="my_model")

        assert "my_model" in result
        assert "created successfully" in result

    def test_create_model_with_type(self, mock_fastmcp_context):
        """Test model creation with specific type."""
        result = create_model(ctx=mock_fastmcp_context, name="thermal_model", model_type="thermal")

        assert "thermal_model" in result
        assert "created successfully" in result

    def test_create_model_updates_active_model(self, mock_fastmcp_context):
        """Test that creating a model updates the active model."""
        create_model(ctx=mock_fastmcp_context, name="active_model")

        context = mock_fastmcp_context.fastmcp._lifespan_result
        assert context.example_instance.active_model == "active_model"

    def test_create_model_updates_history(self, mock_fastmcp_context):
        """Test that create_model updates command history."""
        create_model(ctx=mock_fastmcp_context, name="test")

        context = mock_fastmcp_context.fastmcp._lifespan_result
        assert len(context.command_history) > 0

    def test_create_model_no_connection(self, mock_fastmcp_context):
        """Test create_model when PyExample not connected."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.example_instance = None

        result = create_model(ctx=mock_fastmcp_context, name="test")

        assert "Error: PyExample not connected" in result

    def test_create_model_with_parameters(self, mock_fastmcp_context):
        """Test model creation with additional parameters."""
        result = create_model(
            ctx=mock_fastmcp_context,
            name="param_model",
            model_type="structural",
            parameters={"mesh_size": 0.1, "material": "steel"},
        )

        assert "param_model" in result
        assert "created successfully" in result
        assert "CREATE MODEL" in mock_fastmcp_context.fastmcp._lifespan_result.command_history[-1]


class TestRunSimulationTool:
    """Tests for the run_simulation tool."""

    def test_run_simulation_explicit_model(self, mock_fastmcp_context):
        """Test running simulation on explicit model."""
        create_model(ctx=mock_fastmcp_context, name="test_model")
        result = run_simulation(ctx=mock_fastmcp_context, model_name="test_model")

        assert "Simulation completed" in result
        assert "test_model" in result

    def test_run_simulation_active_model(self, mock_fastmcp_context):
        """Test running simulation on active model."""
        create_model(ctx=mock_fastmcp_context, name="active_model")
        result = run_simulation(ctx=mock_fastmcp_context)

        assert "Simulation completed" in result
        assert "active_model" in result

    def test_run_simulation_saves_results(self, mock_fastmcp_context):
        """Test that simulation results are saved in context."""
        create_model(ctx=mock_fastmcp_context, name="model_with_results")
        run_simulation(ctx=mock_fastmcp_context, model_name="model_with_results", save_results=True)

        context = mock_fastmcp_context.fastmcp._lifespan_result
        assert "model_with_results" in context.simulation_results
        assert context.simulation_results["model_with_results"]["status"] == "completed"

    def test_run_simulation_no_save_results(self, mock_fastmcp_context):
        """Test simulation without saving results."""
        create_model(ctx=mock_fastmcp_context, name="temp_model")
        run_simulation(ctx=mock_fastmcp_context, model_name="temp_model", save_results=False)

        context = mock_fastmcp_context.fastmcp._lifespan_result
        assert "temp_model" not in context.simulation_results

    def test_run_simulation_no_model(self, mock_fastmcp_context):
        """Test simulation with no model specified or active."""
        result = run_simulation(ctx=mock_fastmcp_context)

        assert "Error: No model specified or active" in result

    def test_run_simulation_updates_history(self, mock_fastmcp_context):
        """Test that run_simulation updates command history."""
        create_model(ctx=mock_fastmcp_context, name="sim_model")
        run_simulation(ctx=mock_fastmcp_context, model_name="sim_model")

        context = mock_fastmcp_context.fastmcp._lifespan_result
        # Should have at least 2 commands (create + solve)
        assert len(context.command_history) >= 2

    def test_run_simulation_no_connection(self, mock_fastmcp_context):
        """Test run_simulation when PyExample not connected."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.example_instance = None

        result = run_simulation(ctx=mock_fastmcp_context, model_name="test")

        assert "Error: PyExample not connected" in result


class TestGetCommandHistoryTool:
    """Tests for the get_command_history tool."""

    def test_get_history_list_format(self, mock_fastmcp_context):
        """Test getting history in list format."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.command_history = ["CMD1", "CMD2", "CMD3"]

        result = get_command_history(ctx=mock_fastmcp_context, format="list")

        assert "CMD1" in result
        assert "CMD2" in result
        assert "CMD3" in result

    def test_get_history_numbered_format(self, mock_fastmcp_context):
        """Test getting history in numbered format."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.command_history = ["CMD1", "CMD2"]

        result = get_command_history(ctx=mock_fastmcp_context, format="numbered")

        assert "1. CMD1" in result
        assert "2. CMD2" in result

    def test_get_history_json_format(self, mock_fastmcp_context):
        """Test getting history in JSON format."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.command_history = ["CMD1", "CMD2"]

        result = get_command_history(ctx=mock_fastmcp_context, format="json")

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed == ["CMD1", "CMD2"]

    def test_get_history_empty(self, mock_fastmcp_context):
        """Test getting history when no commands executed."""
        result = get_command_history(ctx=mock_fastmcp_context)

        assert "No commands executed" in result


class TestExecutePythonCodeTool:
    """Tests for the execute_python_code tool."""

    def test_execute_python_code_success(self, mock_fastmcp_context):
        """Test successful Python code execution."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "42\n",
                "stderr": "",
            }
        )

        result = execute_python_code(ctx=mock_fastmcp_context, code="print(42)")

        assert "42" in result

    def test_execute_python_code_with_warnings(self, mock_fastmcp_context):
        """Test Python code execution with warnings."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "Result\n",
                "stderr": "Warning: deprecated\n",
            }
        )

        result = execute_python_code(ctx=mock_fastmcp_context, code="some_code()")

        assert "Result" in result
        assert "Warning" in result
        assert "deprecated" in result

    def test_execute_python_code_error(self, mock_fastmcp_context):
        """Test Python code execution with error."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.python_session.execute = MagicMock(
            return_value={
                "success": False,
                "error": "NameError: name 'undefined' is not defined",
            }
        )

        result = execute_python_code(ctx=mock_fastmcp_context, code="undefined()")

        assert "Error:" in result
        assert "NameError" in result


class TestToolsIntegration:
    """Integration tests for multiple tools working together."""

    def test_complete_workflow(self, mock_fastmcp_context):
        """Test complete workflow using multiple tools."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "Analysis complete\n",
                "stderr": "",
            }
        )

        # Create models
        create_model(ctx=mock_fastmcp_context, name="model1", model_type="structural")
        create_model(ctx=mock_fastmcp_context, name="model2", model_type="thermal")

        # Run simulations
        run_simulation(ctx=mock_fastmcp_context, model_name="model1")
        run_simulation(ctx=mock_fastmcp_context, model_name="model2")

        # Check history
        history = get_command_history(ctx=mock_fastmcp_context, format="numbered")
        assert "CREATE MODEL" in history
        assert "SOLVE MODEL" in history

        # Execute Python code
        code_result = execute_python_code(
            ctx=mock_fastmcp_context, code="print('Analysis complete')"
        )
        assert "Analysis complete" in code_result

        # Verify context state
        assert len(context.simulation_results) == 2
        assert "model1" in context.simulation_results
        assert "model2" in context.simulation_results
