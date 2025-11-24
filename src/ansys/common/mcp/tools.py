"""Legacy module - common tools moved to tools/ directory.

Product-specific tools should be implemented in the respective
product MCP packages (e.g., pymapdl-mcp, pyfluent-mcp).

Common tools are now in:
- ansys.common.mcp.tools.environment: Environment and version checking

Please import from the new locations for future use.
"""

import warnings

# Re-export for backward compatibility
from ansys.common.mcp.tools import (
    check_package_version,
    get_python_environment_info,
)

warnings.warn(
    "Importing from ansys.common.mcp.tools is deprecated. "
    "Please use ansys.common.mcp.tools.environment or specific tool modules instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["check_package_version", "get_python_environment_info"]


