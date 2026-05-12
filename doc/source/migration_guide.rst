.. _migration_guide:

===============
Migration guide
===============

This guide helps you migrate from older versions of ``pyansys-common-mcp`` to the latest version.

Version 0.2.x to 0.3.0 - Command history format change
======================================================

Overview
--------

The format of the ``command_history`` attribute in ``PyAnsysBaseAppContext`` has changed
to support more advanced session management features, including selective command replay
and better error tracking.

What changed
------------

**Old Format (v0.2.x)**

``command_history`` was a simple list of strings:

.. code-block:: python

    command_history: list[str] = field(default_factory=list)

    # Example:
    app_context.command_history = ["import numpy", "x = 10", "print(x)"]

**New Format (v0.3.0+)**

``command_history`` is now a list of lists with three elements:

.. code-block:: python

    command_history: list[list[str | bool]] = field(default_factory=list)

    # Example:
    app_context.command_history = [
        ["python_code", True, "import numpy"],
        ["python_code", True, "x = 10"],
        ["python_code", True, "print(x)"]
    ]

Each entry contains:

1. **Command type** (str): e.g., ``"python_code"``, ``"plot_code"``, or custom types
2. **Success flag** (bool): ``True`` if successful, ``False`` if failed
3. **Command content** (str): The actual code or command executed

Why this changed
----------------

The new format enables:

- **Selective replay**: Restart can replay only successful commands
- **Command filtering**: Filter history by type or success status
- **Better debugging**: Track which commands failed and why
- **Type awareness**: Handle different command types appropriately during replay

Migration steps
---------------

Step 1: Update context initialization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

   This step only applies if you explicitly set ``command_history`` during initialization.
   If you do not, skip to Step 2.

If you manually initialize ``command_history``:

.. code-block:: python

    # OLD
    context = PyAnsysBaseAppContext(
        command_history=["cmd1", "cmd2"]
    )

    # NEW
    context = PyAnsysBaseAppContext(
        command_history=[
            ["python_code", True, "cmd1"],
            ["python_code", True, "cmd2"]
        ]
    )

Step 2: Update history appends
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Update all code that appends to ``command_history`` to use the new ``add_to_history()`` method:

.. code-block:: python

    # OLD
    app_context.command_history.append(command)

    # NEW
    app_context.add_to_history("command_type", True, command)

For example, in a custom tool:

.. code-block:: python

    # OLD
    @app.tool()
    def my_tool(ctx: Context, command: str):
        result = execute_command(command)
        app_context.command_history.append(command)
        return result

    # NEW
    @app.tool()
    def my_tool(ctx: Context, command: str):
        try:
            result = execute_command(command)
            app_context.add_to_history("my_tool", True, command)
            return result
        except Exception as e:
            app_context.add_to_history("my_tool", False, command)
            raise

Step 3: Update history reading
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Update code that reads from ``command_history``:

.. code-block:: python

    # OLD - Direct iteration over strings
    for command in app_context.command_history:
        print(f"Command: {command}")

    # NEW - Unpack the list structure
    for command_type, success, command in app_context.command_history:
        print(f"Type: {command_type}, Success: {success}, Command: {command}")

    # Or access by index
    for entry in app_context.command_history:
        command_type = entry[0]
        success = entry[1]
        command = entry[2]
        print(f"Type: {command_type}, Success: {success}, Command: {command}")

Step 4: Update ``get_command_history`` tool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

   This step only applies if you implemented a custom ``get_command_history`` tool.
   If you did not, skip to Step 5.

If you implemented a custom ``get_command_history`` tool:

.. code-block:: python

    # OLD
    @app.tool()
    def get_command_history(ctx: Context, format: str = "list") -> str:
        app_context = ctx.fastmcp._lifespan_result

        if format == "numbered":
            return "\n".join([f"{i + 1}. {cmd}" for i, cmd in enumerate(app_context.command_history)])
        return "\n".join(app_context.command_history)

    # NEW
    @app.tool()
    def get_command_history(ctx: Context, format: str = "list", code_type: str = "all") -> str:
        app_context = ctx.fastmcp._lifespan_result

        # Filter by code type if specified
        if code_type != "all":
            filtered = [entry for entry in app_context.command_history if entry[0] == code_type]
        else:
            filtered = app_context.command_history

        # Format output - extract just the command content (index 2)
        if format == "numbered":
            return "\n".join([f"{i + 1}. {entry[2]}" for i, entry in enumerate(filtered)])
        elif format == "json":
            return json.dumps([
                {"code_type": e[0], "success": e[1], "command": e[2]}
                for e in filtered
            ], indent=2)
        return "\n".join([entry[2] for entry in filtered])

Step 5: Update session restart logic
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have custom restart logic:

.. code-block:: python

    # OLD
    @app.tool()
    def restart_session(ctx: Context, replay_history: bool = True) -> str:
        app_context = ctx.request_context.lifespan_context
        app_context.python_session.restart()

        if replay_history:
            for cmd in app_context.command_history:
                app_context.python_session.execute(cmd)
        return "Restarted"

    # NEW - Use the built-in function
    from ansys.common.mcp.tools import restart_python_session

    @app.tool()
    def restart_session(ctx: Context, replay_successful: bool = True) -> str:
        return restart_python_session(
            ctx,
            run_successful_history_commands=replay_successful,
            run_all_history=False
        )

Step 6: Record custom commands with ``add_to_history()``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your custom tools run commands outside of ``execute_python_code()`` or
``create_custom_plot()`` (for example, direct API calls to an Ansys product), you must
record those commands in the history manually. Use the ``add_to_history()`` method on
the context so that session restart can replay them correctly.

.. code-block:: python

    @app.tool()
    def run_product_command(ctx: Context, command: str) -> str:
        app_context = ctx.request_context.lifespan_context
        try:
            result = app_context.product_instance.run(command)
            app_context.add_to_history("product_command", True, command)
            return str(result)
        except Exception as e:
            app_context.add_to_history("product_command", False, command)
            raise

.. note::

   Commands that are not added to the history will not be replayed on session restart,
   which may leave the session in an inconsistent state.

Breaking changes checklist
--------------------------

Review this checklist to ensure your migration is complete:

- [ ] Updated all ``command_history.append()`` calls to use ``add_to_history()``
- [ ] Updated all code that reads ``command_history`` to handle the new structure
- [ ] Updated custom history retrieval tools to extract the command content (index 2)
- [ ] Added command type classification for all custom tools
- [ ] Added success/failure tracking to all command executions
- [ ] Recorded all custom commands via ``add_to_history()`` (not only Python/plot commands)
- [ ] Updated any session restart logic to use the new format
- [ ] Updated tests that check ``command_history`` content
- [ ] Updated any custom replay logic to handle command types

Getting help
------------

If you encounter issues during migration:

1. Check the ``examples`` directory for reference implementations
2. Review the test files in ``tests/test_pyexample/`` for usage patterns
3. Open an issue on the GitHub repository with your specific use case
4. See the :ref:`ref_user_guide` for more detailed examples
