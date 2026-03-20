"""Entry point for running PyExample MCP server."""

import sys

# Import tools to register them with the app
import pyexample_mcp.tools  # noqa: F401
from pyexample_mcp import app

from ansys.common.mcp.logging_config import setup_logging


def main():
    """Run the PyExample MCP server."""
    # Setup logging
    setup_logging(level="INFO")

    # Run the server (app instance already has tools registered)
    app.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
