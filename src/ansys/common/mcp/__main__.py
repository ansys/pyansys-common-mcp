"""Entry point for running the MCP server as a module.

Note: This common package is primarily intended to be used as a library
by product-specific MCP servers (e.g., PyMAPDL, PyFluent). It does not
provide a standalone runnable server.

To create a product-specific MCP server, see the examples in the README.
"""

import sys


def main():
    """Provide usage information as the entry point."""
    print(
        "ansys-common-mcp is a library for building PyAnsys MCP servers.\n"
        "It is not meant to be run directly.\n\n"
        "To create a product-specific MCP server, please refer to the documentation:\n"
        "https://github.com/ansys-internal/pyansys-common-mcp\n\n"
        "Example product-specific servers:\n"
        "  - pymapdl-mcp: https://github.com/ansys/pymapdl-mcp\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
