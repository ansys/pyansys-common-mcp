"""Legacy module - functionality moved to server.py and context.py.

This module is kept for backward compatibility but its functionality
has been reorganized into:
- ansys.common.mcp.server: BaseMCPServer and create_mcp_server
- ansys.common.mcp.context: BaseAppContext

Please import from the new locations for future use.
"""

import warnings

# Re-export for backward compatibility
from ansys.common.mcp.context import BaseAppContext as AppContext
from ansys.common.mcp.server import BaseMCPServer, create_mcp_server

warnings.warn(
    "Importing from ansys.common.mcp.mpc is deprecated. "
    "Please use ansys.common.mcp.server and ansys.common.mcp.context instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AppContext", "BaseMCPServer", "create_mcp_server"]
