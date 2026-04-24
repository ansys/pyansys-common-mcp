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
    restart_python,
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
    # Also set request_context.lifespan_context for tools that use it
    context.request_context.lifespan_context = app_context
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
        assert (
            "CREATE MODEL" in mock_fastmcp_context.fastmcp._lifespan_result.command_history[-1][2]
        )


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
        context.command_history = [
            ["example_command", True, "CMD1"],
            ["example_command", True, "CMD2"],
            ["example_command", True, "CMD3"],
        ]

        result = get_command_history(ctx=mock_fastmcp_context, format="list")

        assert "CMD1" in result
        assert "CMD2" in result
        assert "CMD3" in result

    def test_get_history_numbered_format(self, mock_fastmcp_context):
        """Test getting history in numbered format."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.command_history = [
            ["plot_command", True, "CMD1"],
            ["plot_command", True, "CMD2"],
        ]

        result = get_command_history(ctx=mock_fastmcp_context, format="numbered")

        assert "1. CMD1" in result
        assert "2. CMD2" in result

    def test_get_history_json_format(self, mock_fastmcp_context):
        """Test getting history in JSON format."""
        context = mock_fastmcp_context.fastmcp._lifespan_result
        context.command_history = [
            ["python_code", True, "CMD1"],
            ["python_code", True, "CMD2"],
        ]

        result = get_command_history(ctx=mock_fastmcp_context, format="json")

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["command"] == "CMD1"
        assert parsed[1]["command"] == "CMD2"

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


class TestRestartPythonTool:
    """Tests for the restart_python tool."""

    def test_restart_python_success(self, mock_fastmcp_context):
        """Test successful Python session restart."""
        context = mock_fastmcp_context.request_context.lifespan_context
        context.python_session.restart = MagicMock(return_value={"success": True})
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "done",
                "stderr": "",
            }
        )
        context.command_history = [
            ["python_code", True, "x = 10"],
        ]

        result = restart_python(ctx=mock_fastmcp_context)

        assert "successfully" in result.lower()
        context.python_session.restart.assert_called_once()

    def test_restart_python_no_session(self, mock_fastmcp_context):
        """Test restart_python when no session exists."""
        context = mock_fastmcp_context.request_context.lifespan_context
        context.python_session = None

        result = restart_python(ctx=mock_fastmcp_context)

        assert "Error" in result
        assert "No Python session" in result

    def test_restart_python_replay_successful_default(self, mock_fastmcp_context):
        """Test that restart replays successful commands by default."""
        context = mock_fastmcp_context.request_context.lifespan_context
        context.python_session.restart = MagicMock(return_value={"success": True})
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "done",
                "stderr": "",
            }
        )
        context.command_history = [
            ["python_code", True, "a = 1"],
            ["python_code", False, "bad_code"],
            ["python_code", True, "b = 2"],
        ]

        restart_python(ctx=mock_fastmcp_context)

        # Should replay only successful commands (2 calls)
        assert context.python_session.execute.call_count == 2

    def test_restart_python_replay_run_all_and_successful(self, mock_fastmcp_context):
        """Test that restart replays all commands when run_all_history=True."""
        context = mock_fastmcp_context.request_context.lifespan_context
        context.python_session.restart = MagicMock(return_value={"success": True})
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "done",
                "stderr": "",
            }
        )
        context.command_history = [
            ["python_code", True, "a = 1"],
            ["python_code", False, "bad_code"],
            ["python_code", True, "b = 2"],
        ]

        restart_python(
            ctx=mock_fastmcp_context, run_successful_history_commands=True, run_all_history=True
        )

        # Should replay all commands (3 calls)
        assert context.python_session.execute.call_count == 3

    def test_restart_python_no_replay(self, mock_fastmcp_context):
        """Test restart without replaying commands."""
        context = mock_fastmcp_context.request_context.lifespan_context
        context.python_session.restart = MagicMock(return_value={"success": True})
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "done",
                "stderr": "",
            }
        )
        context.command_history = [
            ["python_code", True, "x = 1"],
        ]

        restart_python(
            ctx=mock_fastmcp_context, run_successful_history_commands=False, run_all_history=False
        )

        # Should not replay any commands
        context.python_session.execute.assert_not_called()

    def test_restart_python_replay_all(self, mock_fastmcp_context):
        """Test restart replaying all commands."""
        context = mock_fastmcp_context.request_context.lifespan_context
        context.python_session.restart = MagicMock(return_value={"success": True})
        context.python_session.execute = MagicMock(
            return_value={
                "success": True,
                "stdout": "done",
                "stderr": "",
            }
        )
        context.command_history = [
            ["python_code", True, "x = 1"],
            ["python_code", False, "bad"],
            ["python_code", True, "y = 2"],
        ]

        restart_python(ctx=mock_fastmcp_context, run_all_history=True)

        # Should replay all commands (3 calls)
        assert context.python_session.execute.call_count == 3

    def test_restart_python_exception_handling(self, mock_fastmcp_context):
        """Test restart handles exceptions gracefully."""
        context = mock_fastmcp_context.request_context.lifespan_context
        context.python_session.restart = MagicMock(side_effect=RuntimeError("Restart failed"))

        result = restart_python(ctx=mock_fastmcp_context)

        assert "Error" in result
        assert "Restart failed" in result


# ============================================================================
# restart_python Integration Tests
# ============================================================================


@pytest.mark.integration
class TestRestartPythonIntegration:
    """Integration tests for restart_python with real Python session.

    These tests use actual PersistentPythonSession to verify end-to-end functionality.
    """

    def test_restart_python_with_real_session(self, mock_fastmcp_context):
        """Test restart with real Python session."""
        from ansys.common.mcp.helpers import PersistentPythonSession

        # Get both the fastmcp and request_context references
        context = mock_fastmcp_context.fastmcp._lifespan_result
        mock_fastmcp_context.request_context.lifespan_context = context

        context.python_session = PersistentPythonSession()
        context.python_session.start()

        try:
            # Execute initial Python code
            result1 = execute_python_code(mock_fastmcp_context, "restart_var = 100")
            assert json.loads(result1)["success"]

            # Verify variable exists
            result2 = execute_python_code(mock_fastmcp_context, "print(restart_var)")
            result2_dict = json.loads(result2)
            assert result2_dict["success"]
            assert "100" in result2_dict["stdout"]

            # Restart session
            restart_result = restart_python(mock_fastmcp_context)
            assert "successfully" in restart_result.lower()

            # Verify variable is restored after restart
            result3 = execute_python_code(mock_fastmcp_context, "print(restart_var)")
            result3_dict = json.loads(result3)
            assert result3_dict["success"]
            assert "100" in result3_dict["stdout"]

        finally:
            context.python_session.stop()

    def test_restart_python_clears_variables_no_replay(self, mock_fastmcp_context):
        """Test restart without replay clears all variables."""
        from ansys.common.mcp.helpers import PersistentPythonSession

        context = mock_fastmcp_context.fastmcp._lifespan_result
        mock_fastmcp_context.request_context.lifespan_context = context

        context.python_session = PersistentPythonSession()
        context.python_session.start()

        try:
            # Execute code
            result1 = execute_python_code(mock_fastmcp_context, "temp_var = 999")
            assert json.loads(result1)["success"]

            # Restart without replay
            restart_result = restart_python(
                mock_fastmcp_context, run_successful_history_commands=False, run_all_history=False
            )
            assert "successfully" in restart_result.lower()

            # Variable should not exist
            result2 = execute_python_code(mock_fastmcp_context, "print(temp_var)")
            result2_dict = json.loads(result2)
            assert not result2_dict["success"]
            assert "not defined" in result2_dict["error"].lower()

        finally:
            context.python_session.stop()

    def test_restart_python_with_mixed_commands(self, mock_fastmcp_context):
        """Test restart with mixed successful and failed commands."""
        from ansys.common.mcp.helpers import PersistentPythonSession

        context = mock_fastmcp_context.fastmcp._lifespan_result
        mock_fastmcp_context.request_context.lifespan_context = context

        context.python_session = PersistentPythonSession()
        context.python_session.start()

        try:
            # Execute successful command
            result1 = execute_python_code(mock_fastmcp_context, "success_var = 42")
            assert json.loads(result1)["success"]

            # Execute failed command
            result2 = execute_python_code(mock_fastmcp_context, "print(undefined_variable)")
            assert not json.loads(result2)["success"]

            # Execute another successful command
            result3 = execute_python_code(mock_fastmcp_context, "another_var = 24")
            assert json.loads(result3)["success"]

            # Restart with successful replay only
            restart_result = restart_python(
                mock_fastmcp_context, run_successful_history_commands=True, run_all_history=False
            )
            assert "successfully" in restart_result.lower()

            # Successful variables should exist
            result4 = execute_python_code(mock_fastmcp_context, "print(success_var)")
            result4_dict = json.loads(result4)
            assert result4_dict["success"]
            assert "42" in result4_dict["stdout"]

            result5 = execute_python_code(mock_fastmcp_context, "print(another_var)")
            result5_dict = json.loads(result5)
            assert result5_dict["success"]
            assert "24" in result5_dict["stdout"]

            # Undefined variable should still not exist
            result6 = execute_python_code(mock_fastmcp_context, "print(undefined_variable)")
            result6_dict = json.loads(result6)
            assert not result6_dict["success"]

        finally:
            context.python_session.stop()

    def test_restart_python_with_pyexample_operations(self, mock_fastmcp_context):
        """Test restart after performing PyExample operations."""
        from ansys.common.mcp.helpers import PersistentPythonSession

        context = mock_fastmcp_context.fastmcp._lifespan_result
        mock_fastmcp_context.request_context.lifespan_context = context

        context.python_session = PersistentPythonSession()
        context.python_session.start()

        try:
            # Create PyExample models
            create_model(ctx=mock_fastmcp_context, name="model_a")
            create_model(ctx=mock_fastmcp_context, name="model_b")

            # Execute Python code that uses PyExample data
            result1 = execute_python_code(
                mock_fastmcp_context, "model_count = 2; print(f'Created {model_count} models')"
            )
            assert json.loads(result1)["success"]

            # Restart session
            restart_result = restart_python(mock_fastmcp_context)
            assert "successfully" in restart_result.lower()

            # Python variables should be restored
            result2 = execute_python_code(mock_fastmcp_context, "print(model_count)")
            result2_dict = json.loads(result2)
            assert result2_dict["success"]
            assert "2" in result2_dict["stdout"]

            # PyExample models should still exist (not affected by Python restart)
            assert "model_a" in context.example_instance.models
            assert "model_b" in context.example_instance.models

        finally:
            context.python_session.stop()

    def test_restart_python_preserves_startup_code(self, mock_fastmcp_context):
        """Test that startup code is preserved after restart."""
        from ansys.common.mcp.helpers import PersistentPythonSession

        context = mock_fastmcp_context.fastmcp._lifespan_result
        mock_fastmcp_context.request_context.lifespan_context = context

        context.python_session = PersistentPythonSession(
            startup_code="STARTUP_CONSTANT = 'initialized'"
        )
        context.python_session.start()

        try:
            # Verify startup code ran
            result1 = execute_python_code(mock_fastmcp_context, "print(STARTUP_CONSTANT)")
            result1_dict = json.loads(result1)
            assert result1_dict["success"]
            assert "initialized" in result1_dict["stdout"]

            # Add custom variable
            result2 = execute_python_code(mock_fastmcp_context, "custom_var = 123")
            assert json.loads(result2)["success"]

            # Restart without replay
            restart_result = restart_python(
                mock_fastmcp_context, run_successful_history_commands=False, run_all_history=False
            )
            assert "successfully" in restart_result.lower()

            # Startup constant should still exist
            result3 = execute_python_code(mock_fastmcp_context, "print(STARTUP_CONSTANT)")
            result3_dict = json.loads(result3)
            assert result3_dict["success"]
            assert "initialized" in result3_dict["stdout"]

            # Custom variable should not exist
            result4 = execute_python_code(mock_fastmcp_context, "print(custom_var)")
            result4_dict = json.loads(result4)
            assert not result4_dict["success"]

        finally:
            context.python_session.stop()

    def test_restart_python_complete_workflow(self, mock_fastmcp_context):
        """Test complete workflow with restart in the middle."""
        from ansys.common.mcp.helpers import PersistentPythonSession

        context = mock_fastmcp_context.fastmcp._lifespan_result
        mock_fastmcp_context.request_context.lifespan_context = context

        context.python_session = PersistentPythonSession()
        context.python_session.start()

        try:
            # Phase 1: Initial work
            create_model(ctx=mock_fastmcp_context, name="workflow_model")
            result1 = execute_python_code(mock_fastmcp_context, "phase = 1; data = [1, 2, 3]")
            assert json.loads(result1)["success"]

            # Phase 2: Restart to clean Python state
            restart_result = restart_python(mock_fastmcp_context)
            assert "successfully" in restart_result.lower()

            # Phase 3: Verify state
            # Python variables should be restored
            result2 = execute_python_code(mock_fastmcp_context, "print(phase, data)")
            result2_dict = json.loads(result2)
            assert result2_dict["success"]
            assert "1" in result2_dict["stdout"]
            assert "[1, 2, 3]" in result2_dict["stdout"]

            # PyExample model should still exist
            assert "workflow_model" in context.example_instance.models

            # Phase 4: Continue working
            result3 = execute_python_code(mock_fastmcp_context, "phase = 2; data.append(4)")
            assert json.loads(result3)["success"]

            result4 = execute_python_code(mock_fastmcp_context, "print(data)")
            result4_dict = json.loads(result4)
            assert result4_dict["success"]
            assert "4" in result4_dict["stdout"]

        finally:
            context.python_session.stop()
