.. _user_guide_common_patterns:

===============
Common patterns
===============

This page explains common patterns for building robust MCP servers.

.. note::

   All tool examples use the recommended ``ctx: Context`` parameter pattern to access
   the application context. For more information, see :ref:`function_parameter`.

Initialize a Python session
===========================

Set up a session with startup code
----------------------------------

You can set up a Python session with custom startup code that runs automatically
when the session starts. This approach is useful for importing commonly used libraries,
configuring settings, or defining helper functions.

.. code-block:: python

   from ansys.common.mcp.helpers import PersistentPythonSession

   # Create a session with startup code
   startup_code = """
   import numpy as np
   import pandas as pd
   import matplotlib.pyplot as plt

   # Define a helper function
   def quick_plot(data):
       plt.figure(figsize=(10, 6))
       plt.plot(data)
       plt.show()
   """

   session = PersistentPythonSession(startup_code=startup_code)
   session.start()

   # Now numpy, pandas, and plt are already imported
   result = session.execute("arr = np.array([1, 2, 3, 4, 5])")

When you restart the session using the ``session.restart()`` method, the startup
code runs again, ensuring that all imports and configurations are
reestablished. This approach is particularly useful when resetting the session state
while maintaining necessary dependencies.

Command history
===============

The ``command_history`` attribute in ``PyAnsysBaseAppContext`` tracks all commands executed
during the MCP session. This history is used for session replay when restarting the Python
environment with the ``restart_python_session()`` tool. Each entry in the history includes the command type,
execution success status, and the actual code or command executed.

.. note::

   If you are upgrading from a previous version where ``command_history`` was a simple
   list of strings, see the :ref:`migration_guide` for step-by-step migration instructions.

Format structure
----------------

Each entry in ``command_history`` is a list with three elements:

.. code-block:: python

    [tool, success_flag, tool_arguments]

Where:

- **command_type** (str): The type of command executed. Common values include:

  - ``"python_code"``: Python code executed via ``execute_python_code()``
  - ``"plot_code"``: Plot code executed via ``create_custom_plot()``
  - Custom types defined by product-specific implementations (e.g., ``"example_command"``)

- **success_flag** (bool): Whether the command executed successfully (``True``) or failed (``False``)

- **code_content** (str): The actual code or command that was executed

Example usage
-------------

Accessing command history:

.. code-block:: python

    from ansys.common.mcp import PyAnsysBaseAppContext

    app_context = PyAnsysBaseAppContext()

    # After executing commands, the history might look like:
    # [
    #     ("python_code", True, "import numpy as np"),
    #     ("python_code", True, "x = np.array([1, 2, 3])"),
    #     ("python_code", False, "print(undefined_variable)"),
    #     ("plot_code", True, "plt.plot([1, 2, 3])")
    # ]

Adding entries to command history:

.. code-block:: python

    # For successful execution
    app_context.add_to_history("python_code", True, "result = 42")

    # For failed execution
    app_context.add_to_history("python_code", False, "bad_syntax)")

Filtering command history:

.. code-block:: python

    # Get only successful commands
    successful_commands = [
        entry for entry in app_context.command_history
        if entry[1] == True
    ]

    # Get only python_code tool calls
    python_commands = [
        entry for entry in app_context.command_history
        if entry[0] == "python_code"
    ]

    # Get the actual code from all commands
    all_code = [entry[2] for entry in app_context.command_history]

Best practices
--------------

1. **Always use** ``add_to_history()``: Use ``app_context.add_to_history(tool, success, tool_arguments)``
   instead of appending directly to ``command_history``. This method ensures consistent
   formatting and allows for future enhancements.

2. **Use descriptive command types**: Choose clear, consistent names for your command
   types to make filtering easier.

3. **Update success flag accurately**: Set the success flag based on actual execution
   results, not just whether an exception was raised.

4. **Use skip_history parameter**: When replaying commands during restart, use
   ``skip_history=True`` in ``execute_python_code()`` and ``create_custom_plot()``
   to avoid duplicate history entries:

   .. code-block:: python

       # During restart, skip adding to history
       execute_python_code(ctx, command[2], skip_history=True)

Run Python code from tools
--------------------------

The ``execute_python_code`` tool lets you run arbitrary Python code in the persistent session.
Because the code runs in the context of the session, it has access to all imports and variables
defined in the startup code.

The function automatically tracks all executed code in the ``command_history`` (see
`Command history`_ above), recording both successful and failed executions.

.. code-block:: python

   from mcp.server.fastmcp import Context
   from ansys.common.mcp.tools import execute_python_code

   @mcp.tool()
   def run_python_code(ctx: Context, code: str, timeout: int = 60, skip_history: bool = False) -> str:
       """Run Python code in the persistent session.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected).
       code : str
           Python code to run.
       timeout : int, default: 60
           Maximum time in seconds to allow for code execution before timing out.
       skip_history : bool, default: False
           If True, the executed code will not be added to the command history. This is useful
           when replaying commands during a session restart to avoid duplicate entries.
       """
       # execute_python_code automatically adds to command_history
       # You can add additional logic here (such as logging and error handling)
       return execute_python_code(ctx=ctx, code=code, timeout=timeout, skip_history=skip_history)

Restart a session with history
------------------------------

You can create a tool to restart the Python session while optionally replaying the command history
(see `Format structure`_ above). This approach allows you to reset the session state
while preserving and optionally replaying previous commands.

.. code-block:: python

    from ansys.common.mcp.tools import restart_python_session

   @mcp.tool()
   def restart_session(
       ctx: Context,
       run_successful_history_commands: bool = True,
       run_all_history: bool = False
   ) -> str:
       """Restart the Python session and optionally replay commands.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected).
       run_successful_history_commands : bool, default: True
           Whether to replay only successful command history.
       run_all_history : bool, default: False
           Whether to replay all command history.
       """
       return restart_python_session(
           ctx,
           run_successful_history_commands=run_successful_history_commands,
           run_all_history=run_all_history
       )

.. note::

   ``restart_python_session()`` only replays commands of type ``"python_code"`` and
   ``"plot_code"``. Commands recorded with a custom type (such as ``"example_command"``
   or any product-specific type) are silently skipped.

   If you need to replay custom commands on restart, you must extend
   ``restart_python_session()`` with your own logic. For example:

   .. code-block:: python

       from ansys.common.mcp.tools import restart_python_session

       @mcp.tool()
       def restart_session(ctx: Context) -> str:
           """Restart and replay all command types."""
           app_context = ctx.request_context.lifespan_context

           # Let the built-in function handle python_code and plot_code
           result = restart_python_session(ctx)

           # Replay custom command types manually
           for command_type, success, command in app_context.command_history:
               if command_type == "example_command" and success:
                   app_context.example_instance.run_command(command)

           return result

   .. warning::

      With this approach, the original execution order is not preserved.
      All ``"python_code"`` and ``"plot_code"`` commands are replayed first by
      ``restart_python_session()``, and ``"example_command"`` entries are replayed
      afterwards. If your custom commands depend on state set by Python code, this
      ordering is fine, but if Python code depends on a product state set by a custom
      command, the replay will fail.

      To preserve the original order, implement the full replay loop yourself instead
      of calling ``restart_python_session()``.

Handle errors
=============

Use graceful degradation
-------------------------

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

.. note::

   Logs automatically redirect to stderr (not stdout) to avoid interfering
   with the MCP protocol. The logging configuration handles this behavior.

Add retry logic
---------------

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

Track metadata
==============

Monitor session state
---------------------

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

Manage user preferences
-----------------------

.. code-block:: python

   @mcp.tool()
   def set_preference(ctx: Context, key: str, value: str) -> str:
       """Set a user preference.

       Parameters
       ----------
       ctx : Context
           MCP context (automatically injected).
       key : str
           Preference key.
       value : str
           Preference value.
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
           MCP context (automatically injected).
       key : str
           Preference key.
       default : str, default: None
           Default value if the specified preference key is not found.
       """
       app_context = ctx.request_context.lifespan_context
       prefs = app_context.metadata.get("preferences", {})
       value = prefs.get(key, default)

       if value is None:
           return f"Preference '{key}' is not set."
       return value
