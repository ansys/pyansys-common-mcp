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

"""Common Model Context Protocol (MCP) infrastructure for PyAnsys libraries.

This package provides base classes, utilities, and common tools that
PyAnsys product-specific MCP servers can extend and use.
"""
import importlib.metadata as importlib_metadata

from ansys.common.mcp.context import PyAnsysBaseAppContext
from ansys.common.mcp.helpers import (
    PersistentPythonSession,
)
from ansys.common.mcp.logging_config import get_logger, setup_logging
from ansys.common.mcp.server import PyAnsysBaseMCP
from ansys.common.mcp.tools import (
    create_custom_plot,
    execute_python_code,
)

__all__ = [
    "PyAnsysBaseAppContext",
    "PyAnsysBaseMCP",
    "PersistentPythonSession",
    "setup_logging",
    "get_logger",
    "execute_python_code",
    "create_custom_plot",
]


__version__ = importlib_metadata.version(__name__.replace(".", "-"))
__version__ = importlib_metadata.version(__name__.replace(".", "-"))
"""PyAnsys Common MCP version."""

__all__ = [
"PyAnsysBaseAppContext",
"PyAnsysBaseMCP",
"PersistentPythonSession",
"setup_logging",
"get_logger",
"execute_python_code",
"create_custom_plot",
"__version__",
]
