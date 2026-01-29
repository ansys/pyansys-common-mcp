.. _user_guide_advanced_patterns:

=================
Advanced patterns
=================

This section covers advanced techniques for building robust MCP servers.

.. note::

   All tool examples use the recommended ``ctx: Context`` parameter pattern for accessing
   the application context. See :ref:`user_guide_architecture` for details.

Python session
==============

Execute Python code from tools
-------------------------------

.. code-block:: python

   from mcp.server.fastmcp import Context

   @mcp.tool()
   def run_python_script(ctx: Context, code: str) -> str:
       """Execute Python code in the persistent session.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected)
       code : str
           Python code to execute
       """
       app_context = ctx.request_context.lifespan_context
       result = app_context.python_session.execute(code)
       return result["stdout"] if result["success"] else f"Error: {result['error']}"


Session restart with history
-----------------------------

.. code-block:: python

   @mcp.tool()
   def restart_session(ctx: Context, replay_history: bool = True) -> str:
       """Restart Python session and optionally replay commands.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected)
       replay_history : bool
           Whether to replay command history
       """
       app_context = ctx.request_context.lifespan_context

       history = app_context.command_history.copy()
       result = app_context.python_session.restart()

       if not result["success"]:
           return f"Restart failed: {result['error']}"

       if replay_history and history:
           for cmd in history:
               app_context.python_session.execute(cmd)
           return f"Restarted and replayed {len(history)} commands"

       return "Session restarted"


Command history
===============

Create and export command history
---------------------------------

.. code-block:: python

   from mcp.server.fastmcp import Context

   @mcp.tool()
   def execute_command(ctx: Context, command: str) -> str:
       """Execute and track command.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected)
       command : str
           Command to execute
       """
       app_context = ctx.request_context.lifespan_context
       result = app_context.product_instance.run(command)
       if result["success"]:
           app_context.command_history.append(command)
       return result

   @mcp.tool()
   def export_history(ctx: Context, format: str = "json") -> str:
       """Export command history as JSON or text.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected)
       format : str
           Export format ('json' or 'text')
       """
       app_context = ctx.request_context.lifespan_context

       if format == "json":
           import json
           return json.dumps(app_context.command_history, indent=2)
       return "\n".join(app_context.command_history)


Error handling
==============

Graceful degradation
--------------------

Handle errors without crashing the server:

.. code-block:: python

   from ansys.common.mcp.logging_config import get_logger

   logger = get_logger(__name__)

   def product_startup(self):
       """Start with graceful error handling."""
       try:
           logger.info("Attempting to connect to product...")
           self.context.product_instance = connect(timeout=30)
           logger.info(f"Connected: {self.context.product_instance}")

       except ConnectionTimeout as e:
           logger.error(f"Connection timeout: {e}")
           logger.warning("Server will start in limited mode")
           self.context.product_instance = None
           self.context.metadata["mode"] = "limited"

       except Exception as e:
           logger.error(f"Unexpected error during startup: {e}")
           raise  # Re-raise for critical errors

Retry logic
-----------

Implement retry logic for flaky connections:

.. code-block:: python

   import time

   def product_startup(self):
       """Connect with retry logic."""
       max_retries = 3
       retry_delay = 5  # seconds

       for attempt in range(1, max_retries + 1):
           try:
               logger.info(f"Connection attempt {attempt}/{max_retries}...")
               self.context.product_instance = connect()
               logger.info("Connected successfully")
               return

           except Exception as e:
               logger.warning(f"Attempt {attempt} failed: {e}")

               if attempt < max_retries:
                   logger.info(f"Retrying in {retry_delay} seconds...")
                   time.sleep(retry_delay)
               else:
                   logger.error("All connection attempts failed")
                   raise


Metadata
========

Track session state
-------------------

.. code-block:: python

   from datetime import datetime
   import uuid

   def product_startup(self):
       """Initialize with state tracking."""
       self.context.product_instance = connect()
       self.context.metadata.update({
           "session_id": str(uuid.uuid4()),
           "start_time": datetime.now().isoformat(),
           "statistics": {"commands_executed": 0, "errors": 0}
       })

User preferences
----------------

.. code-block:: python

   @mcp.tool()
   def set_preference(ctx: Context, key: str, value: str) -> str:
       """Set a user preference.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected)
       key : str
           Preference key
       value : str
           Preference value
       """
       app_context = ctx.request_context.lifespan_context
       app_context.metadata.setdefault("preferences", {})[key] = value
       logger.info(f"Set {key} = {value}")
       return json.dumps(
           {
               "success": True,
               "stdout": "",
               "stderr": "",
               "message": "Preference updated",
           },
           ensure_ascii=False,
           indent=2,
       )

   @mcp.tool()
   def get_preference(ctx: Context, key: str, default: str = None) -> str:
       """Get a user preference.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected)
       key : str
           Preference key
       default : str, optional
           Default value if not found
       """
       app_context = ctx.request_context.lifespan_context
       prefs = app_context.metadata.get("preferences", {})
       value = prefs.get(key, default)

       if value is None:
           return f"Preference '{key}' not set"
       return value
