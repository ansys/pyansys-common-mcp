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

"""Unit tests for server module."""

from unittest.mock import MagicMock, patch

import pytest

from ansys.common.mcp.context import PyAnsysBaseAppContext
from ansys.common.mcp.server import PyAnsysBaseMCP


class MockMCP(PyAnsysBaseMCP):
    """Mock implementation of PyAnsysBaseMCP for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize mock MCP server for testing."""
        self.product_startup_called = False
        self.product_cleanup_called = False
        super().__init__(*args, **kwargs)

    def product_startup(self):
        """Mock product startup."""
        self.product_startup_called = True

    def product_cleanup(self):
        """Mock product cleanup."""
        self.product_cleanup_called = True


class TestPyAnsysBaseMCPInitialization:
    """Tests for PyAnsysBaseMCP initialization."""

    def test_mcp_initialization_defaults(self):
        """Test MCP initialization with defaults."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mcp = MockMCP()

            assert mcp.python_executable is None
            assert mcp.working_directory is None

    def test_mcp_initialization_with_python_executable(self):
        """Test MCP initialization with custom python executable."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            executable = "/custom/python"
            mcp = MockMCP(python_executable=executable)

            assert mcp.python_executable == executable

    def test_mcp_initialization_with_working_directory(self):
        """Test MCP initialization with working directory."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            work_dir = "/tmp/workspace"
            mcp = MockMCP(working_directory=work_dir)

            assert mcp.working_directory == work_dir

    def test_mcp_initialization_stores_parameters(self):
        """Test that MCP initialization stores parameters correctly."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            executable = "/usr/bin/python3"
            work_dir = "/home/user/project"

            mcp = MockMCP(python_executable=executable, working_directory=work_dir)

            assert mcp.python_executable == executable
            assert mcp.working_directory == work_dir


class TestPyAnsysBaseMCPAbstractMethods:
    """Tests for abstract methods in PyAnsysBaseMCP."""

    def test_product_startup_is_abstract(self):
        """Test that product_startup must be implemented."""
        with pytest.raises(TypeError):

            class IncompleteImpl(PyAnsysBaseMCP):
                def product_cleanup(self):
                    pass

            IncompleteImpl()

    def test_product_cleanup_is_abstract(self):
        """Test that product_cleanup must be implemented."""
        with pytest.raises(TypeError):

            class IncompleteImpl(PyAnsysBaseMCP):
                def product_startup(self):
                    pass

            IncompleteImpl()


class TestPyAnsysBaseMCPCreateContext:
    """Tests for create_context method."""

    def test_create_context_returns_base_context(self):
        """Test that create_context returns PyAnsysBaseAppContext."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                mcp = MockMCP()
                context = mcp.create_context()

                assert isinstance(context, PyAnsysBaseAppContext)

    def test_create_context_creates_python_session(self):
        """Test that create_context creates a PersistentPythonSession."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession") as mock_session:
                mcp = MockMCP(python_executable="/custom/python")

                # Verify session is not created before calling create_context
                mock_session.assert_not_called()

                mcp.create_context()

                # Verify PersistentPythonSession was instantiated
                mock_session.assert_called()

    def test_create_context_initializes_empty_history(self):
        """Test that create_context initializes empty command history."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                mcp = MockMCP()
                context = mcp.create_context()

                assert context.command_history == []

    def test_create_context_includes_startup_code(self):
        """Test that startup code is included when creating context."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession") as mock_session:
                mcp = MockMCP()
                mcp.create_context()

                # Check that the session was created with startup code
                call_kwargs = mock_session.call_args[1]
                assert "startup_code" in call_kwargs
                startup = call_kwargs["startup_code"]
                assert "matplotlib" in startup
                assert "Agg" in startup
                assert "pyvista" in startup

    def test_create_context_docstring_example(self):
        """Test the example from create_context docstring."""
        # The docstring shows creating a custom context subclass
        # Verify this pattern works

        from dataclasses import dataclass
        from typing import Any, Optional

        @dataclass
        class MockMCPContext(PyAnsysBaseAppContext):
            mock_instance: Optional[Any] = None

        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):

            class MockMCPC(PyAnsysBaseMCP):
                def create_context(self) -> MockMCPContext:
                    return MockMCPContext(
                        python_session=MagicMock(),
                        command_history=[],
                        mock_instance="mock_instance_value",
                    )

                def product_startup(self):
                    pass

                def product_cleanup(self):
                    pass

            mcp = MockMCPC()
            context = mcp.create_context()

            assert isinstance(context, MockMCPContext)
            assert context.mock_instance == "mock_instance_value"
            assert isinstance(context, PyAnsysBaseAppContext)


class TestPyAnsysBaseMCPSessionManagement:
    """Tests for session management methods."""

    def test_start_python_session(self):
        """Test start_python_session method."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mock_session = MagicMock()
            mock_session.start.return_value = {"success": True, "stdout": "started"}

            mcp = MockMCP()
            mcp.context = MagicMock()
            mcp.context.python_session = mock_session
            mcp.context.python_executable = None

            with patch("ansys.common.mcp.server.logger") as mock_logger:
                mcp.start_python_session()

                mock_session.start.assert_called_once()
                mock_logger.info.assert_called()

    def test_cleanup_python_session(self):
        """Test cleanup_python_session method."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mock_session = MagicMock()
            mock_session.is_running.return_value = True
            mock_session.stop.return_value = {"success": True}

            mcp = MockMCP()
            mcp.context = MagicMock()
            mcp.context.python_session = mock_session

            with patch("ansys.common.mcp.server.logger"):
                mcp.cleanup_python_session()

                mock_session.is_running.assert_called()
                mock_session.stop.assert_called_once()

    def test_cleanup_python_session_not_running(self):
        """Test cleanup_python_session when session is not running."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mock_session = MagicMock()
            mock_session.is_running.return_value = False

            mcp = MockMCP()
            mcp.context = MagicMock()
            mcp.context.python_session = mock_session

            with patch("ansys.common.mcp.server.logger"):
                mcp.cleanup_python_session()

                # stop() should not be called if not running
                mock_session.stop.assert_not_called()

    def test_cleanup_python_session_handles_exception(self):
        """Test cleanup_python_session handles exceptions."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mock_session = MagicMock()
            mock_session.is_running.return_value = True
            mock_session.stop.side_effect = RuntimeError("Stop failed")

            mcp = MockMCP()
            mcp.context = MagicMock()
            mcp.context.python_session = mock_session

            with patch("ansys.common.mcp.server.logger"):
                # Should not raise an exception
                mcp.cleanup_python_session()


class TestPyAnsysBaseMCPLifespan:
    """Tests for product_lifespan context manager."""

    @pytest.mark.asyncio
    async def test_product_lifespan_basic_flow(self):
        """Test basic flow of product_lifespan."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mcp = MockMCP()

                    mock_server = MagicMock()

                    # Test the lifespan context manager
                    async with mcp.product_lifespan(mock_server) as context:
                        assert mcp.server is mock_server
                        assert mcp.context is not None
                        assert isinstance(context, PyAnsysBaseAppContext)

                    # After exiting, cleanup should be called
                    assert mcp.product_cleanup_called

    @pytest.mark.asyncio
    async def test_product_lifespan_calls_startup(self):
        """Test that product_lifespan calls product_startup."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mcp = MockMCP()

                    mock_server = MagicMock()

                    async with mcp.product_lifespan(mock_server):
                        assert mcp.product_startup_called

    @pytest.mark.asyncio
    async def test_product_lifespan_cleanup_on_exception(self):
        """Test that cleanup is called even if exception occurs."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mcp = MockMCP()

                    mock_server = MagicMock()

                    try:
                        async with mcp.product_lifespan(mock_server):
                            raise ValueError("Test exception")
                    except ValueError:
                        pass

                    # Cleanup should still be called
                    assert mcp.product_cleanup_called


class TestPyAnsysBaseMCPIntegration:
    """Integration tests for PyAnsysBaseMCP."""

    def test_mcp_implementation_complete(self):
        """Test that MockMCP is a complete implementation."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mcp = MockMCP(python_executable="/usr/bin/python", working_directory="/tmp/test")

            assert mcp.python_executable == "/usr/bin/python"
            assert mcp.working_directory == "/tmp/test"
            assert callable(mcp.product_startup)
            assert callable(mcp.product_cleanup)
            assert callable(mcp.create_context)


class TestPyAnsysBaseMCPErrors:
    """Tests for error handling in PyAnsysBaseMCP."""

    def test_start_python_session_with_none_context(self):
        """Test start_python_session raises AttributeError with None context."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.logger"):
                mcp = MockMCP()
                mcp.context = None

                # Should raise AttributeError when trying to access context.python_executable
                with pytest.raises(AttributeError):
                    mcp.start_python_session()

    def test_cleanup_python_session_with_none_context(self):
        """Test cleanup_python_session raises AttributeError with None context."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.logger"):
                mcp = MockMCP()
                mcp.context = None

                # Should raise AttributeError when trying to access context.python_session
                with pytest.raises(AttributeError):
                    mcp.cleanup_python_session()


class TestPyAnsysBaseMCPStartupCode:
    """Tests for startup code generation."""

    def test_startup_code_includes_matplotlib(self):
        """Test startup code configures matplotlib."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession") as mock_session:
                mcp = MockMCP()
                mcp.create_context()

                call_kwargs = mock_session.call_args[1]
                startup = call_kwargs["startup_code"]

                assert "matplotlib" in startup
                assert "Agg" in startup

    def test_startup_code_includes_pyvista(self):
        """Test startup code configures pyvista."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession") as mock_session:
                mcp = MockMCP()
                mcp.create_context()

                call_kwargs = mock_session.call_args[1]
                startup = call_kwargs["startup_code"]

                assert "pyvista" in startup
                assert "OFF_SCREEN" in startup

    def test_startup_code_includes_plot_functions(self):
        """Test startup code defines plot save functions."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession") as mock_session:
                mcp = MockMCP()
                mcp.create_context()

                call_kwargs = mock_session.call_args[1]
                startup = call_kwargs["startup_code"]

                assert "save_plot" in startup
                assert "save_matplotlib_plot" in startup
                assert "base64" in startup


class TestPyAnsysBaseMCPNeedPython:
    """Tests for need_python property and Python session management."""

    def test_need_python_default_is_true(self):
        """Test that need_python defaults to True."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mcp = MockMCP()
            assert mcp.need_python is True

    def test_need_python_can_be_set_to_false(self):
        """Test that need_python can be set to False."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mcp = MockMCP()
            mcp.need_python = False
            assert mcp.need_python is False

    def test_need_python_can_be_set_to_true(self):
        """Test that need_python can be set to True."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mcp = MockMCP()
            mcp.need_python = False
            mcp.need_python = True
            assert mcp.need_python is True

    def test_need_python_property_getter(self):
        """Test that need_python property getter returns _need_python."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mcp = MockMCP()
            # Check internal state
            assert mcp._need_python is True
            # Check property getter
            assert mcp.need_python is True

    def test_need_python_property_setter(self):
        """Test that need_python property setter updates _need_python."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            mcp = MockMCP()
            mcp.need_python = False
            # Check internal state
            assert mcp._need_python is False
            # Check property getter
            assert mcp.need_python is False

    @pytest.mark.asyncio
    async def test_lifespan_starts_python_session_when_need_python_true(self):
        """Test that product_lifespan starts Python session when need_python is True."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mcp = MockMCP()
                    mcp.need_python = True

                    mock_server = MagicMock()

                    with patch.object(mcp, "start_python_session") as mock_start:
                        async with mcp.product_lifespan(mock_server):
                            pass

                        # Verify start_python_session was called
                        mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_skips_python_session_when_need_python_false(self):
        """Test that product_lifespan skips Python session when need_python is False."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mcp = MockMCP()
                    mcp.need_python = False

                    mock_server = MagicMock()

                    with patch.object(mcp, "start_python_session") as mock_start:
                        async with mcp.product_lifespan(mock_server):
                            pass

                        # Verify start_python_session was NOT called
                        mock_start.assert_not_called()

    @pytest.mark.asyncio
    async def test_lifespan_cleans_up_python_session_when_need_python_true(self):
        """Test that product_lifespan cleans up Python session when need_python is True."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mcp = MockMCP()
                    mcp.need_python = True

                    mock_server = MagicMock()

                    with patch.object(mcp, "cleanup_python_session") as mock_cleanup:
                        async with mcp.product_lifespan(mock_server):
                            pass

                        # Verify cleanup_python_session was called
                        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_skips_cleanup_python_session_when_need_python_false(self):
        """Test that product_lifespan skips cleanup when need_python is False."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mcp = MockMCP()
                    mcp.need_python = False

                    mock_server = MagicMock()

                    with patch.object(mcp, "cleanup_python_session") as mock_cleanup:
                        async with mcp.product_lifespan(mock_server):
                            pass

                        # Verify cleanup_python_session was NOT called
                        mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_lifespan_always_calls_product_startup_regardless_of_need_python(self):
        """Test that product_startup is always called regardless of need_python."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mock_server = MagicMock()

                    # Test with need_python = True
                    mcp_true = MockMCP()
                    mcp_true.need_python = True
                    async with mcp_true.product_lifespan(mock_server):
                        pass
                    assert mcp_true.product_startup_called

                    # Test with need_python = False
                    mcp_false = MockMCP()
                    mcp_false.need_python = False
                    async with mcp_false.product_lifespan(mock_server):
                        pass
                    assert mcp_false.product_startup_called

    @pytest.mark.asyncio
    async def test_lifespan_always_calls_product_cleanup_regardless_of_need_python(self):
        """Test that product_cleanup is always called regardless of need_python."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            with patch("ansys.common.mcp.server.PersistentPythonSession"):
                with patch("ansys.common.mcp.server.logger"):
                    mock_server = MagicMock()

                    # Test with need_python = True
                    mcp_true = MockMCP()
                    mcp_true.need_python = True
                    async with mcp_true.product_lifespan(mock_server):
                        pass
                    assert mcp_true.product_cleanup_called

                    # Test with need_python = False
                    mcp_false = MockMCP()
                    mcp_false.need_python = False
                    async with mcp_false.product_lifespan(mock_server):
                        pass
                    assert mcp_false.product_cleanup_called

    def test_need_python_can_be_set_in_subclass_init(self):
        """Test that need_python can be configured in subclass __init__."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):

            class CustomMCP(PyAnsysBaseMCP):
                """Custom MCP that disables Python session."""

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.need_python = False

                def product_startup(self):
                    pass

                def product_cleanup(self):
                    pass

            mcp = CustomMCP()
            assert mcp.need_python is False

    def test_need_python_python_executable_parameter(self):
        """Test need_python with python_executable parameter."""
        with patch("ansys.common.mcp.server.FastMCP.__init__", return_value=None):
            executable = "/custom/python"
            mcp = MockMCP(python_executable=executable)

            assert mcp.need_python is True  # Default behavior
            assert mcp.python_executable == executable

            mcp.need_python = False
            assert mcp.need_python is False
            # python_executable should still be stored even when need_python is False
            assert mcp.python_executable == executable
