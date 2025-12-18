"""Unit tests for context module."""

import pytest

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
        
    def test_context_metadata_isolated(self):
        """Test that metadata dict is isolated between instances."""
        context1 = PyAnsysBaseAppContext()
        context2 = PyAnsysBaseAppContext()
        
        context1.metadata["key"] = "value1"
        
        assert "key" not in context2.metadata
        assert context1.metadata != context2.metadata
        
    def test_context_command_history_isolated(self):
        """Test that command_history list is isolated between instances."""
        context1 = PyAnsysBaseAppContext()
        context2 = PyAnsysBaseAppContext()
        
        context1.command_history.append("cmd1")
        
        assert "cmd1" not in context2.command_history
        assert context1.command_history != context2.command_history
        
    def test_context_modification(self):
        """Test modifying context attributes."""
        context = PyAnsysBaseAppContext()
        
        # Add metadata
        context.metadata["key1"] = "value1"
        context.metadata["key2"] = "value2"
        assert len(context.metadata) == 2
        
        # Add command history
        context.command_history.append("cmd1")
        context.command_history.append("cmd2")
        assert len(context.command_history) == 2
        
        # Update product instance
        context.product_instance = "new_product"
        assert context.product_instance == "new_product"
        
    def test_context_python_executable_property(self):
        """Test python_executable attribute."""
        context = PyAnsysBaseAppContext()
        
        context.python_executable = "/path/to/python"
        assert context.python_executable == "/path/to/python"
        
    def test_context_product_instance_various_types(self):
        """Test product_instance with various types."""
        # With string
        context1 = PyAnsysBaseAppContext(product_instance="string_value")
        assert context1.product_instance == "string_value"
        
        # With dict
        context2 = PyAnsysBaseAppContext(product_instance={"key": "value"})
        assert context2.product_instance == {"key": "value"}
        
        # With object
        class CustomProduct:
            pass
        
        product = CustomProduct()
        context3 = PyAnsysBaseAppContext(product_instance=product)
        assert context3.product_instance is product


class TestContextExtension:
    """Tests for extending PyAnsysBaseAppContext."""
    
    def test_context_subclass_creation(self):
        """Test creating a custom context subclass."""
        from dataclasses import dataclass
        from typing import Optional, Any
        
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
        
    def test_context_subclass_with_inheritance(self):
        """Test context subclass with inherited attributes."""
        from dataclasses import dataclass
        
        @dataclass
        class ExtendedContext(PyAnsysBaseAppContext):
            extra_field: str = "default"
        
        context = ExtendedContext(
            product_instance="test",
            extra_field="custom",
        )
        
        assert context.product_instance == "test"
        assert context.extra_field == "custom"
        assert context.metadata == {}
        assert context.command_history == []


class TestContextDataclass:
    """Tests for dataclass functionality of PyAnsysBaseAppContext."""
    
    def test_context_equality(self):
        """Test context equality comparison."""
        context1 = PyAnsysBaseAppContext(product_instance="test")
        context2 = PyAnsysBaseAppContext(product_instance="test")
        context3 = PyAnsysBaseAppContext(product_instance="different")
        
        assert context1 == context2
        assert context1 != context3
        
    def test_context_repr(self):
        """Test context string representation."""
        context = PyAnsysBaseAppContext(product_instance="test")
        repr_str = repr(context)
        
        assert "PyAnsysBaseAppContext" in repr_str
        assert "test" in repr_str
        
    def test_context_copy(self):
        """Test copying context values."""
        from dataclasses import replace
        
        context1 = PyAnsysBaseAppContext(
            product_instance="original",
            python_executable="/path/to/python",
        )
        
        context2 = replace(context1, product_instance="modified")
        
        assert context1.product_instance == "original"
        assert context2.product_instance == "modified"
        assert context1.python_executable == context2.python_executable


class TestContextUsagePatterns:
    """Tests for common usage patterns with context."""
    
    def test_context_as_state_container(self):
        """Test using context as a state container."""
        context = PyAnsysBaseAppContext()
        
        # Add various state
        context.metadata["session_id"] = "session_123"
        context.metadata["user_id"] = "user_456"
        context.command_history.append("import numpy")
        context.command_history.append("x = 10")
        
        # Retrieve state
        assert context.metadata["session_id"] == "session_123"
        assert len(context.command_history) == 2
        assert context.command_history[0] == "import numpy"
        
    def test_context_with_nested_data(self):
        """Test context with nested data structures."""
        context = PyAnsysBaseAppContext()
        
        context.metadata["nested"] = {
            "level1": {
                "level2": {
                    "value": "deep"
                }
            }
        }
        
        assert context.metadata["nested"]["level1"]["level2"]["value"] == "deep"
        
    def test_context_metadata_clear(self):
        """Test clearing metadata."""
        context = PyAnsysBaseAppContext()
        context.metadata["key"] = "value"
        
        context.metadata.clear()
        
        assert len(context.metadata) == 0
        
    def test_context_command_history_clear(self):
        """Test clearing command history."""
        context = PyAnsysBaseAppContext()
        context.command_history.append("cmd1")
        context.command_history.append("cmd2")
        
        context.command_history.clear()
        
        assert len(context.command_history) == 0
