.. _user_guide_architecture:

============
Architecture
============

This section explains the architecture of PyAnsys Common MCP and how components work together.

Overview
========

PyAnsys Common MCP follows a layered architecture with clear separation of concerns:

.. mermaid::

   flowchart TD
       A["AI Client<br/>(Claude, ChatGPT)"]
       B["Your Product MCP Server<br/>• Custom Context<br/>• Product Startup/Cleanup<br/>• MCP Tools"]
       C["PyAnsysBaseMCP<br/>(Base Class)<br/>• Lifecycle orchestration<br/>• Python session management<br/>• Context creation & injection<br/>• Error handling & logging"]
       D["FastMCP<br/>(MCP Protocol Library)<br/>• MCP protocol implementation<br/>• Tool registration & execution<br/>• Transport layer (stdio)"]

       A -->|"MCP Protocol (stdio)"| B
       B -.->|extends| C
       C -.->|uses| D

       style A fill:#e1f5ff
       style B fill:#fff4e1
       style C fill:#e8f5e9
       style D fill:#f3e5f5

Core components
===============

PyAnsysBaseMCP
--------------

Base class for all PyAnsys product-specific MCP servers.

**Responsibilities:** Lifecycle orchestration, Python session management, context injection, error handling.

.. important::

   **Methods you must implement:**

   - ``product_startup()`` - Initialize your product connection
   - ``product_cleanup()`` - Clean up your product connection

   These methods are abstract and must be implemented in your subclass.
   Failing to do so will raise a ``TypeError`` at instantiation time.

**Methods you can optionally override:**

- ``create_context()`` - Override only if using a custom context class (returns ``PyAnsysBaseAppContext`` by default)

**Methods already implemented:**

- ``start_python_session()`` - Starts persistent Python subprocess
- ``cleanup_python_session()`` - Stops Python session
- ``product_lifespan()`` - Manages complete server lifecycle

PyAnsysBaseAppContext
---------------------

A dataclass that holds shared state accessible from all MCP tools.

**Built-in fields:**

.. code-block:: python

   @dataclass
   class PyAnsysBaseAppContext:
       product_instance: Optional[Any] = None
       python_executable: Optional[Any] = None
       python_session: Optional[Any] = None  # PersistentPythonSession
       metadata: dict = field(default_factory=dict)
       command_history: list = field(default_factory=list)


**Extending the context:**

Product-specific servers can extend this to add custom fields:

.. code-block:: python

   from dataclasses import dataclass
   from typing import Optional
   from ansys.common.mcp import PyAnsysBaseAppContext

   @dataclass
   class MyProductContext(PyAnsysBaseAppContext):
       """Extended dataclass for MyProduct MCP context."""
       custom_field: Optional[str] = None


.. tip::

    If you need a custom field, you can either extend this class or use the
    ``metadata`` dict to store arbitrary key-value pairs.


Context injection
=================

Context is injected into tools via FastMCP's dependency system. There are two ways to access it:

Method 1: Function parameter (recommended)
------------------------------------------

Declare ``ctx: Context`` as a parameter - FastMCP automatically injects it:

.. code-block:: python

   from mcp.server.fastmcp import Context

   @mcp.tool()
   def my_tool(ctx: Context, param: str) -> str:
       """Execute something.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected, don't pass manually)
       param : str
           Your parameter
       """
       # Access application context
       app_context = ctx.request_context.lifespan_context

       # Access product instance
       result = app_context.product_instance.run(param)

       # Add to command history if successful
       if result["success"]:
            app_context.command_history.append(param)

       return result

.. note::

    Always include ``ctx: Context`` as the first parameter to ensure proper injection.
    This also enforces implementation of critical methods like ``product_startup()``
    and ``product_cleanup()`` in your server class.

.. note::

    Do not attempt to pass ``ctx`` manually when calling the tool - it is handled
    automatically by the framework.


Method 2: ``get_context()`` function
------------------------------------

Another way is to import and call ``get_context()`` inside the tool function.
This retrieves the current context instance.

.. code-block:: python

   from fastmcp.server.dependencies import get_context

   @mcp.tool()
   def my_tool(param: str) -> str:
       """Execute something."""
       ctx = get_context()
       app_context = ctx.fastmcp._lifespan_result

       result = app_context.product_instance.do_something(param)
       app_context.command_history.append(f"my_tool({param})")
       return result


Lifecycle management
====================

Server lifecycle is managed automatically by ``product_lifespan``:

**Phases:**

1. Create Context
2. Start Python Session
3. **Product Startup** ← Your code
4. Server runs (handles requests)
5. **Product Cleanup** ← Your code
6. Stop Python Session

Using ABC ensures that product-specific servers implement ``product_startup()``
and ``product_cleanup()``. Forgetting these would cause runtime errors, so we
catch them at instantiation:

.. code-block:: python

   # This will raise TypeError if methods not implemented
   server = MyProductMCP()
   # TypeError: Can't instantiate abstract class MyProductMCP with abstract methods product_cleanup, product_startup

Why async lifespan?
-------------------

**Reason:** FastMCP uses async/await for all operations

The MCP protocol is inherently asynchronous. FastMCP handles all the async
complexity internally. The ``product_lifespan`` is an async context manager
that integrates with FastMCP's event loop.

**Note:** Your ``product_startup()`` and ``product_cleanup()`` are regular
(synchronous) functions - the async part is handled by the framework.


Logging
=======

Logs go to **stderr** (not stdout) to avoid interfering with MCP protocol.

**Setup:**

.. code-block:: python

   from ansys.common.mcp.logging_config import setup_logging, get_logger

   setup_logging(level="INFO")  # or use LOGLEVEL env variable
   logger = get_logger(__name__)

   logger.info("Starting...")
   logger.error("Error occurred")
