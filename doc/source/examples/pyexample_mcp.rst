.. _ref_pyexample_mcp:

=============
PyExample-MCP
=============

This section walks through a complete, minimal MCP server implementation for a
hypothetical PyAnsys library called "PyExample".

Project structure
-----------------

.. code-block:: text

   pyexample-mcp/
   ├── pyproject.toml
   ├── README.md
   └── src/
       └── pyexample_mcp/
           ├── __init__.py
           ├── __main__.py
           ├── server.py
           └── context.py

Step 1: Context definition
---------------------------

**File:** ``src/pyexample_mcp/context.py``

.. code-block:: python

   """Context for PyExample MCP server."""
   from dataclasses import dataclass, field
   from typing import Optional, Any
   from ansys.common.mcp import PyAnsysBaseAppContext

   @dataclass
   class PyExampleContext(PyAnsysBaseAppContext):
       """Application context for PyExample MCP server.

       Attributes
       ----------
       example_instance : Optional[Any]
           The connected PyExample instance
       active_model : Optional[str]
           Currently active model name
       simulation_results : dict
           Storage for simulation results
       """
       example_instance: Optional[Any] = None
       active_model: Optional[str] = None
       simulation_results: dict = field(default_factory=dict)

Step 2: Server and tool implementation
---------------------------------------

**File:** ``src/pyexample_mcp/server.py``

.. code-block:: python

   """MCP server for PyExample."""
   from typing import Optional
   from fastmcp.server.dependencies import get_context
   from ansys.common.mcp import PyAnsysBaseMCP, PersistentPythonSession
   from ansys.common.mcp.logging_config import get_logger
   from pyexample_mcp.context import PyExampleContext

   logger = get_logger(__name__)

   # Create the MCP server instance
   app = PyAnsysBaseMCP(
       name="pyexample-mcp",
   )

   class PyExampleMCP(PyAnsysBaseMCP):
       """MCP Server for PyExample.

       This server enables AI assistants to interact with PyExample
       for simulation and analysis workflows.
       """

       def __init__(
           self,
           launch_mode: str = "local",
           timeout: int = 60,
           *args,
           **kwargs
       ):
           """Initialize PyExample MCP server.

           Parameters
           ----------
           launch_mode : str
               Launch mode for PyExample ('local' or 'remote')
           timeout : int
               Connection timeout in seconds
           """
           self.launch_mode = launch_mode
           self.timeout = timeout
           super().__init__(*args, **kwargs)

       def create_context(self) -> PyExampleContext:
           """Create PyExample-specific context.

           Returns
           -------
           PyExampleContext
               Context instance with Python session and command history
           """
           # Custom startup code for PyExample workflows
           startup_code = """
   # Standard scientific libraries
   import numpy as np
   import pandas as pd
   import matplotlib
   matplotlib.use('Agg')  # Non-interactive backend
   import matplotlib.pyplot as plt

   # PyVista for 3D visualization
   import pyvista as pv
   pv.OFF_SCREEN = True

   # PyExample library
   import pyexample

   print("PyExample MCP session initialized")
   """

           return PyExampleContext(
               python_session=PersistentPythonSession(
                   python_executable=self.python_executable,
                   working_directory=self.working_directory,
                   startup_code=startup_code
               ),
               command_history=[],
           )

       def product_startup(self):
           """Launch PyExample instance when server starts.

           This method is called automatically during server startup.
           """
           logger.info(f"Launching PyExample in {self.launch_mode} mode...")

           try:
               # Import PyExample (would be real import in actual implementation)
               # from pyexample import launch_example
               # self.context.example_instance = launch_example(
               #     mode=self.launch_mode,
               #     timeout=self.timeout
               # )

               # Simulated for example purposes
               class MockExample:
                   def __init__(self, mode):
                       self.mode = mode
                       self.version = "1.0.0"

                   def run_command(self, cmd):
                       return f"Executed: {cmd}"

                   def exit(self):
                       pass

               self.context.example_instance = MockExample(self.launch_mode)

               logger.info(
                   f"PyExample {self.context.example_instance.version} "
                   f"launched successfully"
               )

           except Exception as e:
               logger.error(f"Failed to launch PyExample: {e}")
               raise

       def product_cleanup(self):
           """Clean up PyExample instance when server stops.

           This method is called automatically during server shutdown.
           """
           if self.context.example_instance:
               try:
                   logger.info("Closing PyExample instance...")
                   self.context.example_instance.exit()
                   logger.info("PyExample instance closed successfully")
               except Exception as e:
                   logger.error(f"Error during PyExample cleanup: {e}")


Step 3: Tool implementation
---------------------------


**File:** ``src/pyexample_mcp/tools.py``

.. code-block:: python

   """Tools for PyExample MCP server."""

   from ansys.example_mcp.server import app
   from ansys.common.mcp import get_context
   from ansys.common.mcp.logging_config
   import get_logger logger = get_logger(__name__)

   # Define tools for interacting with PyExample instance
   @app.tool()
   def execute_command(command: str) -> str:
       """Execute a PyExample command.

       Parameters
       ----------
       command : str
           PyExample command to execute

       Returns
       -------
       str
           Command execution result
       """
       ctx = get_context()
       app_context = ctx.fastmcp._lifespan_result

       if not app_context.example_instance:
           return "Error: PyExample not connected"

       try:
           result = app_context.example_instance.run_command(command)
           app_context.command_history.append(command)
           logger.info(f"Executed command: {command}")
           return result
       except Exception as e:
           logger.error(f"Command execution failed: {e}")
           return f"Error: {e}"


   @app.tool()
   def create_model(
       name: str,
       model_type: str = "default",
       parameters: Optional[dict] = None
   ) -> str:
       """Create a new model in PyExample.

       Parameters
       ----------
       name : str
           Name for the new model
       model_type : str
           Type of model to create
       parameters : Optional[dict]
           Model creation parameters

       Returns
       -------
       str
           Status message
       """
       ctx = get_context()
       app_context = ctx.fastmcp._lifespan_result

       if not app_context.example_instance:
           return "Error: PyExample not connected"

       params = parameters or {}

       # Create model (simulated)
       command = f"CREATE MODEL {name} TYPE {model_type}"
       result = app_context.example_instance.run_command(command)

       # Update context
       app_context.active_model = name
       app_context.command_history.append(command)

       logger.info(f"Created model: {name} (type: {model_type})")
       return f"Model '{name}' created successfully\n{result}"


   @app.tool()
   def run_simulation(
       model_name: Optional[str] = None,
       save_results: bool = True
   ) -> str:
       """Run a simulation on the specified model.

       Parameters
       ----------
       model_name : Optional[str]
           Model to simulate (uses active model if not specified)
       save_results : bool
           Whether to save results in context

       Returns
       -------
       str
           Simulation results summary
       """
       ctx = get_context()
       app_context = ctx.fastmcp._lifespan_result

       if not app_context.example_instance:
           return "Error: PyExample not connected"

       # Determine which model to use
       target_model = model_name or app_context.active_model

       if not target_model:
           return "Error: No model specified or active"

       # Run simulation (simulated)
       command = f"SOLVE MODEL {target_model}"
       result = app_context.example_instance.run_command(command)

       # Save results if requested
       if save_results:
           app_context.simulation_results[target_model] = {
               "status": "completed",
               "summary": result
           }

       app_context.command_history.append(command)
       logger.info(f"Simulation completed for model: {target_model}")

       return f"Simulation completed for '{target_model}'\n{result}"


   @app.tool()
   def get_command_history(format: str = "list") -> str:
       """Retrieve command execution history.

       Parameters
       ----------
       format : str
           Output format: 'list', 'numbered', or 'json'

       Returns
       -------
       str
           Command history in requested format
       """
       ctx = get_context()
       app_context = ctx.fastmcp._lifespan_result

       if not app_context.command_history:
           return "No commands executed yet"

       if format == "numbered":
           lines = [
               f"{i+1}. {cmd}"
               for i, cmd in enumerate(app_context.command_history)
           ]
           return "\n".join(lines)

       elif format == "json":
           import json
           return json.dumps(app_context.command_history, indent=2)

       else:  # list format
           return "\n".join(app_context.command_history)


   @app.tool()
   def execute_python_code(code: str) -> str:
       """Execute Python code in the persistent session.

       This allows for custom analysis and processing using the
       full Python ecosystem.

       Parameters
       ----------
       code : str
           Python code to execute

       Returns
       -------
       str
           Execution output
       """
       ctx = get_context()
       app_context = ctx.fastmcp._lifespan_result

       result = app_context.python_session.execute(code)

       if result["success"]:
           output = result["stdout"]
           if result["stderr"]:
               output += f"\n\nWarnings:\n{result['stderr']}"
           return output
       else:
           return f"Error: {result['error']}"


Step 3: Package initialization
-------------------------------

**File:** ``src/pyexample_mcp/__init__.py``

.. code-block:: python

   """PyExample MCP Server.

   MCP server for PyExample enabling AI-assisted simulation workflows.
   """
   from pyexample_mcp.server import PyExampleMCP, app
   from pyexample_mcp.context import PyExampleContext

   __version__ = "0.1.0"

   __all__ = [
       "PyExampleMCP",
       "PyExampleContext",
       "app",
       "__version__",
   ]


Step 4: Entry point
--------------------

**File:** ``src/pyexample_mcp/__main__.py``

.. code-block:: python

   """Entry point for running PyExample MCP server."""
   import sys
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


Step 5: Package configuration
------------------------------

**File:** ``pyproject.toml``

.. code-block:: toml

   [build-system]
   requires = ["flit_core >=3.2,<4"]
   build-backend = "flit_core.buildapi"

   [project]
   name = "pyexample-mcp"
   version = "0.1.0"
   description = "MCP server for PyExample"
   readme = "README.md"
   requires-python = ">=3.10,<3.14"
   license = { file = "LICENSE" }

   dependencies = [
       "ansys-common-mcp>=0.0.1",
       "pyexample>=1.0.0",  # Your PyAnsys library
   ]

   [project.optional-dependencies]
   dev = [
       "pytest>=7.0",
       "pytest-asyncio>=0.21.0",
       "pytest-mock>=3.10",
   ]

   [project.scripts]
   pyexample-mcp = "pyexample_mcp.__main__:main"

Running the example
-------------------

.. code-block:: bash

   # Install in development mode
   pip install -e .

   # Run the server
   python -m pyexample_mcp

   # Or use the installed script
   pyexample-mcp
