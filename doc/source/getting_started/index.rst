.. _ref_getting_started:

===============
Getting started
===============

Introduction
============

PyAnsys Common MCP is a foundational library that helps you build Model Context Protocol (MCP) servers. These servers let AI assistants interact with Ansys products through PyAnsys libraries.

This section shows how to create your first MCP server in under 30 minutes. For architectural concepts and advanced patterns, see the :ref:`ref_user_guide`.

**Target audience:** PyAnsys library developers who create MCP servers for their products.

Installation
============

Here are the requirements for PyAnsys Common MCP:

- Python 3.10 or later (up to 3.13)
- A PyAnsys library for your product (such as PyMAPDL or PyFluent)

Install in user mode
--------------------

Install in user mode from the private PyPI. Set the ``PYANSYS_PYPI_PRIVATE_PAT`` environment variable:

.. code-block:: bash

   pip install ansys-common-mcp --extra-index-url https://${{ secrets.PYANSYS_PYPI_PRIVATE_PAT }}@pkgs.dev.azure.com/pyansys/_packaging/pyansys/pypi/simple/

Install in developer mode
-------------------------

If you want to contribute to PyAnsys Common MCP or create custom servers, install in developer mode:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/ansys/pyansys-common-mcp.git
   cd pyansys-common-mcp

   # Install in editable mode with development dependencies
   pip install -e .[dev]

   # Or install documentation dependencies for building documentation
   pip install -e .[doc]

Verify installation
-------------------

Verify the installation by importing the package:

.. code-block:: python

   >>> from ansys.common.mcp import PyAnsysBaseMCP, PyAnsysBaseAppContext
   >>> from ansys.common.mcp import PersistentPythonSession

Quick start
===========

Create a minimal working MCP server by following these steps.

Create a package
----------------

Create a package with this project structure:

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

Define a custom context
-----------------------

Create ``context.py`` to store product-specific state:

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

The context stores the shared state accessible from all tools. For information on context management, see :ref:`user_guide_architecture`.

Implement the MCP server
------------------------

Create a file named ``server.py`` to define your server class. Implement the ``product_startup()`` and ``product_cleanup()`` methods. Optionally, override the ``create_context()`` method if you use a custom context class.

.. code-block:: python

   # src/my_product_mcp/server.py
   from ansys.common.mcp import PyAnsysBaseMCP, PersistentPythonSession
   from my_product_mcp.context import MyProductContext
   from my_product import connect  # Your product's API

   class MyProductMCP(PyAnsysBaseMCP):
       """MCP server for MyProduct."""

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
           """Initialize the product connection when the server starts."""
           self.context.product_instance = connect()
           print(f"Connected to MyProduct: {self.context.product_instance}")

       def product_cleanup(self):
           """Clean up the product connection when the server stops."""
           if self.context.product_instance:
               self.context.product_instance.disconnect()
               print("Disconnected from MyProduct")

Create MCP tools
----------------

Create a file named ``tools.py`` to define the capabilities that your server exposes:

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
               Command to execute.

           Returns
           -------
           str
               Command result.
           """
           # Access context via dependency injection
           ctx = get_context()
           app_context = ctx.fastmcp._lifespan_result

           # Run the command using the product instance
           result = app_context.product_instance.run(command)

           # Track the command in history
           app_context.command_history.append(command)

           return result

For more information on context injection patterns, see :ref:`user_guide_architecture`.

Wire everything together
------------------------

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

Configure the package
---------------------

Create the ``pyproject.toml`` file:

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

Run the server
--------------

Install and run:

.. code-block:: bash

   # Install in development mode
   pip install -e .

   # Run the server
   python -m my_product_mcp

The server starts and communicates using stdio. It is ready to accept MCP requests from AI clients.

Next steps
==========

Your MCP server is ready. Explore these sections:

- :ref:`ref_user_guide`: Learn how the framework works and discover advanced patterns.
- :ref:`ref_examples`: See complete working examples like `PyMAPDL-MCP <pymapdl_mcp_>`_
