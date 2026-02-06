"""Common Model Context Protocol (MCP) infrastructure for PyAnsys libraries.

This package provides base classes, utilities, and common tools that
PyAnsys product-specific MCP servers can extend and use.
"""

__version__ = "0.0.1"

from ansys.common.mcp.context import PyAnsysBaseAppContext
from ansys.common.mcp.helpers import (
    PersistentPythonSession,
    generate_rule_from_error,
    update_rules,
)
from ansys.common.mcp.logging_config import get_logger, setup_logging
from ansys.common.mcp.prompts import RULES_SYSTEM_PROMPT
from ansys.common.mcp.server import PyAnsysBaseMCP
from ansys.common.mcp.tools import (
    create_custom_plot,
    get_rules,
    execute_python_code,
)

__all__ = [
    "PyAnsysBaseAppContext",
    "PyAnsysBaseMCP",
    "PersistentPythonSession",
    "generate_rule_from_error",
    "update_rules",
    "setup_logging",
    "get_logger",
    "execute_python_code",
    "create_custom_plot",
    "get_rules",
    "RULES_SYSTEM_PROMPT",
    "__version__",
]
