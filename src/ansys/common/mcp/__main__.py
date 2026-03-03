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

"""Entry point for running the MCP server as a module.

**Note:** This common package is primarily intended to be used as a library
by product-specific MCP servers (such as PyMAPDL or PyFluent). It does not
provide a standalone runnable server.

To create a product-specific MCP server, see the examples in the README.
"""

import sys


def main():
    """Provide usage information. This is the main entry point for module execution."""
    print(
        "ansys-common-mcp is a library for building PyAnsys MCP servers.\n"
        "It is not meant to be run directly.\n\n"
        "To create a product-specific MCP server, see the documentation:\n"
        "https://github.com/ansys/pyansys-common-mcp\n\n"
        "For example product-specific servers, see:\n"
        "  - pymapdl-mcp: https://github.com/ansys/pymapdl-mcp\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
