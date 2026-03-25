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

"""Unit tests for the mock PyExample library."""

from pyexample_mcp.mock_pyexample import (
    Model,
    PyExample,
    SimulationResult,
    launch_pyexample,
)
import pytest


class TestModel:
    """Tests for the Model class."""

    def test_model_creation(self):
        """Test basic model creation."""
        model = Model(name="test_model", model_type="structural")

        assert model.name == "test_model"
        assert model.model_type == "structural"
        assert model.status == "created"
        assert model.id is not None

    def test_model_with_parameters(self):
        """Test model creation with parameters."""
        params = {"length": 10, "width": 5}
        model = Model(name="test", model_type="thermal", parameters=params)

        assert model.parameters == params

    def test_model_repr(self):
        """Test model string representation."""
        model = Model(name="my_model", model_type="default")
        repr_str = repr(model)

        assert "my_model" in repr_str
        assert "default" in repr_str


class TestSimulationResult:
    """Tests for the SimulationResult class."""

    def test_simulation_result_creation(self):
        """Test simulation result creation."""
        result = SimulationResult(
            model_name="test_model",
            status="converged",
            convergence_iterations=10,
            max_stress=250.5,
            displacement=0.05,
        )

        assert result.model_name == "test_model"
        assert result.status == "converged"
        assert result.convergence_iterations == 10
        assert result.max_stress == 250.5
        assert result.displacement == 0.05

    def test_simulation_result_summary(self):
        """Test simulation result summary."""
        result = SimulationResult(
            model_name="beam",
            status="converged",
            convergence_iterations=7,
            max_stress=150.0,
            displacement=0.02,
        )

        summary = result.summary()
        assert "beam" in summary
        assert "converged" in summary
        assert "150.00" in summary


class TestPyExample:
    """Tests for the PyExample class."""

    def test_pyexample_initialization(self):
        """Test PyExample initialization."""
        pe = PyExample(mode="local", timeout=30)

        assert pe.mode == "local"
        assert pe.timeout == 30
        assert pe.version == "2026.1.0"
        assert pe.is_connected is True
        assert pe.active_model is None

    def test_pyexample_with_port(self):
        """Test PyExample initialization with custom port."""
        pe = PyExample(port=50000)

        assert pe.port == 50000

    def test_run_command_create_model(self):
        """Test creating model via run_command."""
        pe = PyExample()
        result = pe.run_command("CREATE MODEL mymodel TYPE structural")

        assert "mymodel" in result
        assert "created successfully" in result
        assert "mymodel" in pe.models
        assert pe.active_model == "mymodel"

    def test_run_command_solve_model(self):
        """Test solving model via run_command."""
        pe = PyExample()
        pe.run_command("CREATE MODEL testmodel")
        result = pe.run_command("SOLVE MODEL testmodel")

        assert "solved successfully" in result
        assert pe.models["testmodel"].status == "solved"

    def test_run_command_list_models(self):
        """Test listing models via run_command."""
        pe = PyExample()
        pe.run_command("CREATE MODEL model1")
        pe.run_command("CREATE MODEL model2")

        result = pe.run_command("LIST MODELS")

        assert "model1" in result
        assert "model2" in result

    def test_run_command_status(self):
        """Test status command."""
        pe = PyExample()
        pe.run_command("CREATE MODEL test")
        result = pe.run_command("STATUS")

        assert "PyExample" in result
        assert "1 models" in result

    def test_create_model(self):
        """Test create_model method."""
        pe = PyExample()
        model = pe.create_model("my_model", model_type="thermal", temp=300)

        assert isinstance(model, Model)
        assert model.name == "my_model"
        assert model.model_type == "thermal"
        assert model.parameters["temp"] == 300
        assert pe.active_model == "my_model"

    def test_solve_with_model_name(self):
        """Test solve method with explicit model name."""
        pe = PyExample()
        pe.create_model("test_model")
        result = pe.solve("test_model")

        assert isinstance(result, SimulationResult)
        assert result.model_name == "test_model"
        assert result.status == "converged"
        assert result.convergence_iterations > 0

    def test_solve_active_model(self):
        """Test solve method using active model."""
        pe = PyExample()
        pe.create_model("active_model")
        result = pe.solve()

        assert result.model_name == "active_model"

    def test_solve_no_model_raises(self):
        """Test solve raises error when no model is specified."""
        pe = PyExample()

        with pytest.raises(ValueError, match="No model specified"):
            pe.solve()

    def test_solve_nonexistent_model_raises(self):
        """Test solve raises error for nonexistent model."""
        pe = PyExample()

        with pytest.raises(ValueError, match="not found"):
            pe.solve("nonexistent")

    def test_get_model(self):
        """Test get_model method."""
        pe = PyExample()
        pe.create_model("my_model")

        model = pe.get_model("my_model")
        assert model.name == "my_model"

    def test_get_model_not_found_raises(self):
        """Test get_model raises error for nonexistent model."""
        pe = PyExample()

        with pytest.raises(ValueError, match="not found"):
            pe.get_model("nonexistent")

    def test_list_models(self):
        """Test list_models method."""
        pe = PyExample()
        pe.create_model("model1")
        pe.create_model("model2")

        models = pe.list_models()

        assert len(models) == 2
        assert all(isinstance(m, Model) for m in models)

    def test_exit(self):
        """Test exit method."""
        pe = PyExample()
        pe.create_model("test")

        pe.exit()

        assert pe.is_connected is False
        assert len(pe.models) == 0
        assert pe.active_model is None

    def test_repr(self):
        """Test PyExample string representation."""
        pe = PyExample(mode="remote")
        repr_str = repr(pe)

        assert "PyExample" in repr_str
        assert "remote" in repr_str


class TestLaunchPyExample:
    """Tests for the launch_pyexample function."""

    def test_launch_default(self):
        """Test launching with defaults."""
        pe = launch_pyexample()

        assert isinstance(pe, PyExample)
        assert pe.mode == "local"
        assert pe.timeout == 60

    def test_launch_custom_parameters(self):
        """Test launching with custom parameters."""
        pe = launch_pyexample(mode="grpc", timeout=120, port=50001)

        assert pe.mode == "grpc"
        assert pe.timeout == 120
        assert pe.port == 50001
