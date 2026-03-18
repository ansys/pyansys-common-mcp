.. _ref_pymapdl_mcp:

PyMAPDL-MCP
===========

Explore the `PyMAPDL-MCP <pymapdl_mcp_>`_ repository for a production-ready, real-world implementation. It provides a complete MCP server for PyMAPDL, offering these benefits:

- **Fully integrates with MAPDL**: Launch, control, and interact with MAPDL.
- **Provides comprehensive tools**: Create geometry, mesh, solve, and postprocess.
- **Offers advanced features**: Manage sessions, plot, and extract results.
- **Follows production patterns**: Handle errors, log, and test.

Key functions
-------------

- ``launch_mapdl()``: Start a MAPDL instance with configurable parameters.
- ``run_mapdl_commands()``: Execute APDL commands.
- ``run_python_code()``: Execute Python code in a persistent session.
- ``screenshot()``: Capture and return MAPDL graphics.

Installation
------------

This package is not publicly available on PyPI. Install it with the following command:

.. code-block:: bash

    pip install ansys-mapdl-mcp --extra-index-url https://${{ secrets.PYANSYS_PYPI_PRIVATE_PAT }}@pkgs.dev.azure.com/pyansys/_packaging/pyansys/pypi/simple/

Usage with Claude Desktop
-------------------------

.. code-block:: json

   {
     "pymapdl-mcp": {
       "pymapdl": {
         "command": "python",
         "args": ["-m", "ansys.mapdl.mcp"]
       }
     }
   }
