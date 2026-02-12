.. _ref_pymapdl_mcp:

===============
PyMAPDL-MCP
===============

For a production-ready and real-world implementation, you can explore
`PyMAPDL-MCP <pymapdl_mcp_>`_ which is a complete MCP server for PyMAPDL.
It demonstrates:

- **Full MAPDL integration** - Launch, control, and interact with MAPDL
- **Comprehensive tools** - Geometry creation, meshing, solving, post-processing
- **Advanced features** - Session management, plotting, result extraction
- **Production patterns** - Error handling, logging, testing

Key Tools
---------

- ``launch_mapdl`` - Start MAPDL instance with configurable parameters
- ``run_mapdl_commands`` - Execute APDL commands
- ``run_python_code`` - Execute Python code in persistent session
- ``screenshot`` - Capture and return MAPDL graphics

Installation
------------

The package is not publicly available on PyPI. You can install it using:

.. code-block:: bash

    pip install ansys-mapdl-mcp --extra-index-url https://${{ secrets.PYANSYS_PYPI_PRIVATE_PAT }}@pkgs.dev.azure.com/pyansys/_packaging/pyansys/pypi/simple/


Usage with Claude Desktop
--------------------------

.. code-block:: json

   {
     "pymapdl-mcp": {
       "pymapdl": {
         "command": "python",
         "args": ["-m", "ansys.mapdl.mcp"],
       }
     }
   }

