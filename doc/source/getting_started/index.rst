.. _ref_getting_started:

===============
Getting started
===============

Introduction
============

PyAnsys Common MCP is a foundational library for building Model Context Protocol (MCP) servers
that enable AI assistants to interact with Ansys products through PyAnsys libraries.

This guide will help you create your first MCP server in under 30 minutes. For detailed
architectural concepts and advanced patterns, see the :ref:`ref_user_guide`.

**Target Audience:** PyAnsys library developers creating MCP servers for their products.

Installation
============

Requirements
------------

- Python 3.10 or later (up to 3.13)
- PyAnsys library for your product (e.g., PyMAPDL, PyFluent)

Standard installation
---------------------

Install from the private PyPI (requires the ``PYANSYS_PYPI_PRIVATE_PAT`` environment variable) :

.. code-block:: bash

   pip install ansys-common-mcp --extra-index-url https://${{ secrets.PYANSYS_PYPI_PRIVATE_PAT }}@pkgs.dev.azure.com/pyansys/_packaging/pyansys/pypi/simple/

Development installation
------------------------

For developers contributing to PyAnsys Common MCP or creating custom servers:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/ansys/pyansys-common-mcp.git
   cd pyansys-common-mcp

   # Install in editable mode with dev dependencies
   pip install -e .[dev]

   # Or for documentation building
   pip install -e .[doc]

Verify installation
-------------------

Verify the installation by importing the package:

.. code-block:: python

   >>> from ansys.common.mcp import PyAnsysBaseMCP, PyAnsysBaseAppContext
   >>> from ansys.common.mcp import PersistentPythonSession
   >>> print("Installation successful!")

Quick start
===========

Create a minimal working MCP server in six steps.

Project structure
-----------------

Create a new package:

.. code-block:: text

   my-product-mcp/
   ├── pyproject.toml
   ├── README.md
   └── src/
       └── my_product_mcp/
           ├── __init__.py
           ├── __main__.py
           ├── server.py       # Your MCP server class
           ├── context.py      # Your custom context
           └── tools.py        # Your MCP tools

Step 1: Define custom context
------------------------------

Create ``context.py`` to hold product-specific state:

.. code-block:: python

   # src/my_product_mcp/context.py
   from dataclasses import dataclass
   from typing import Optional, Any
   from ansys.common.mcp import PyAnsysBaseAppContext

   @dataclass
   class MyProductContext(PyAnsysBaseAppContext):
       """Context for MyProduct MCP server.

       Attributes
       ----------
       product_instance : Optional[Any]
           The connected product instance
       """
       product_instance: Optional[Any] = None

The context holds shared state accessible from all tools. See :ref:`user_guide_architecture` for details on context management.

Step 2: Implement MCP server
-----------------------------

Create ``server.py`` with your server class:

.. code-block:: python

   # src/my_product_mcp/server.py
   from ansys.common.mcp import PyAnsysBaseMCP, PersistentPythonSession
   from my_product_mcp.context import MyProductContext
   from my_product import connect  # Your product's API

   class MyProductMCP(PyAnsysBaseMCP):
       """MCP Server for MyProduct."""

       def create_context(self) -> MyProductContext:
           """Create product-specific context."""
           return MyProductContext(
               python_session=PersistentPythonSession(
                   python_executable=self.python_executable,
                   working_directory=self.working_directory,
               ),
               command_history=[],
           )

       def product_startup(self):
           """Initialize product connection when server starts."""
           self.context.product_instance = connect()
           print(f"Connected to MyProduct: {self.context.product_instance}")

       def product_cleanup(self):
           """Clean up product connection when server stops."""
           if self.context.product_instance:
               self.context.product_instance.disconnect()
               print("Disconnected from MyProduct")

**Required methods:** ``product_startup()`` and ``product_cleanup()``.

**Optional:** Override ``create_context()`` only if using a custom context class.

Step 3: Create MCP tools
-------------------------

Create ``tools.py`` to define the capabilities your server exposes:

.. code-block:: python

   # src/my_product_mcp/tools.py
   from fastmcp.server.dependencies import get_context

   def register_tools(mcp):
       """Register all product-specific MCP tools."""

       @mcp.tool()
       def execute_command(command: str) -> str:
           """Execute a product command.

           Parameters
           ----------
           command : str
               Command to execute

           Returns
           -------
           str
               Command result
           """
           # Access context via dependency injection
           ctx = get_context()
           app_context = ctx.fastmcp._lifespan_result

           # Execute command using product instance
           result = app_context.product_instance.run(command)

           # Track in history
           app_context.command_history.append(command)

           return result

See :ref:`user_guide_architecture` for details on context injection patterns.

Step 4: Wire everything together
--------------------------------

Create ``__init__.py``:

.. code-block:: python

   # src/my_product_mcp/__init__.py
   from my_product_mcp.server import MyProductMCP
   from my_product_mcp.context import MyProductContext
   from my_product_mcp.tools import register_tools

   __all__ = ["MyProductMCP", "MyProductContext", "register_tools"]

Create ``__main__.py`` for CLI execution:

.. code-block:: python

   # src/my_product_mcp/__main__.py
   import sys
   from my_product_mcp import MyProductMCP, register_tools

   def main():
       """Run the MCP server."""
       # Initialize server
       mcp = MyProductMCP(name="my-product-mcp")

       # Register tools
       register_tools(mcp)

       # Run the server
       mcp.run()
       return 0

   if __name__ == "__main__":
       sys.exit(main())

Step 5: Configure package
--------------------------

Create ``pyproject.toml``:

.. code-block:: toml

   [build-system]
   requires = ["flit_core >=3.2,<4"]
   build-backend = "flit_core.buildapi"

   [project]
   name = "my-product-mcp"
   version = "0.1.0"
   description = "MCP server for MyProduct"
   requires-python = ">=3.10,<3.14"
   dependencies = [
       "ansys-common-mcp>=0.0.1",
       "my-product-pyansys>=1.0.0",  # Your PyAnsys library
   ]

   [project.scripts]
   my-product-mcp = "my_product_mcp.__main__:main"

Step 6: Run Your Server
------------------------

Install and run:

.. code-block:: bash

   # Install in development mode
   pip install -e .

   # Run the server
   python -m my_product_mcp

The server will start and communicate via stdio, ready to accept MCP requests from AI clients.

Next Steps
==========

Your MCP server is ready! Continue with:

- :ref:`ref_user_guide` - Understand how the framework works and learn advanced patterns
- :ref:`ref_examples` - See complete working examples like `PyMAPDL-MCP <pymapdl_mcp>`_
