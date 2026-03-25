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

"""Tests for context module."""

from ansys.common.mcp.context import PyAnsysBaseAppContext
from ansys.common.mcp.helpers import PersistentPythonSession


class TestPyAnsysBaseAppContext:
    """Tests for PyAnsysBaseAppContext dataclass."""

    def test_context_initialization_defaults(self):
        """Test context initialization with default values."""
        context = PyAnsysBaseAppContext()

        assert context.product_instance is None
        assert context.python_executable is None
        assert context.python_session is None
        assert context.metadata == {}
        assert context.command_history == []

    def test_context_initialization_with_values(self):
        """Test context initialization with provided values."""
        session = PersistentPythonSession()
        metadata = {"key": "value"}
        history = ["cmd1", "cmd2"]

        context = PyAnsysBaseAppContext(
            product_instance="test_product",
            python_executable="/usr/bin/python",
            python_session=session,
            metadata=metadata,
            command_history=history,
        )

        assert context.product_instance == "test_product"
        assert context.python_executable == "/usr/bin/python"
        assert context.python_session is session
        assert context.metadata == metadata
        assert context.command_history == history

    def test_context_as_state_container(self):
        """Test using context to track session state."""
        context = PyAnsysBaseAppContext()

        # Add state
        context.metadata["session_id"] = "session_123"
        context.command_history.append("import numpy")
        context.command_history.append("x = 10")

        # Retrieve state
        assert context.metadata["session_id"] == "session_123"
        assert len(context.command_history) == 2
        assert context.command_history[0] == "import numpy"


class TestContextExtension:
    """Tests for extending PyAnsysBaseAppContext."""

    def test_context_subclass_creation(self):
        """Test creating a custom context subclass for product-specific use."""
        from dataclasses import dataclass
        from typing import Any, Optional

        @dataclass
        class CustomContext(PyAnsysBaseAppContext):
            custom_field: Optional[Any] = None
            custom_config: dict = None

            def __post_init__(self):
                if self.custom_config is None:
                    self.custom_config = {}

        context = CustomContext(custom_field="test_value")

        assert context.custom_field == "test_value"
        assert context.custom_config == {}
        assert context.product_instance is None  # Inherited from base
