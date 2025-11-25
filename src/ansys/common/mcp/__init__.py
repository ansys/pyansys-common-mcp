"""Common Model Context Protocol (MCP) infrastructure for PyAnsys libraries.

This package provides base classes, utilities, and common tools that
PyAnsys product-specific MCP servers can extend and use.
"""

__version__ = "0.0.1"

from ansys.common.mcp.context import PyAnsysBaseAppContext
from ansys.common.mcp.helpers import PersistentPythonSession
from ansys.common.mcp.server import PyAnsysBaseMCP
from ansys.common.mcp.tools import (
    check_package_version,
    get_python_environment_info,
)

__all__ = [
    "PyAnsysBaseAppContext",
    "PyAnsysBaseMCP",
    "check_package_version",
    "get_python_environment_info",
    "PersistentPythonSession",
    "__version__",
]
