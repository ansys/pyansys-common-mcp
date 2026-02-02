"""Common Model Context Protocol (MCP) infrastructure for PyAnsys libraries.

This package provides base classes, utilities, and common tools that
PyAnsys product-specific MCP servers can extend and use.
"""

__version__ = "0.0.1"

from ansys.common.mcp.context import PyAnsysBaseAppContext
from ansys.common.mcp.helpers import PersistentPythonSession
from ansys.common.mcp.logging_config import get_logger, setup_logging
from ansys.common.mcp.server import PyAnsysBaseMCP

__all__ = [
    "PyAnsysBaseAppContext",
    "PyAnsysBaseMCP",
    "PersistentPythonSession",
    "setup_logging",
    "get_logger",
    "__version__",
]
