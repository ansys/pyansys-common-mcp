





:class:`PersistentPythonSession`
================================


.. py:class:: src.ansys.common.mcp.helpers.PersistentPythonSession(python_executable: Optional[str] = None, startup_code: Optional[str] = None, working_directory: Optional[str] = None)

   
   Maintains a persistent Python subprocess for stateful code execution.

   This class allows multiple code snippets to be executed in the same
   Python session, preserving variables, imports, and state between
   executions. This is essential for LLM workflows where code is generated
   and executed in multiple steps.

   :Parameters:

       **python_executable** : :obj:`Optional`\[:class:`python:str`]
           Path to the Python executable to use. If None, uses sys.executable.

       **startup_code** : :obj:`Optional`\[:class:`python:str`]
           Python code to execute when the session starts (e.g., imports).

       **working_directory** : :obj:`Optional`\[:class:`python:str`]
           Working directory for the Python process. If None, uses the current directory.













   .. rubric:: Examples

   Create a persistent session and execute multiple steps:

   >>> session = PersistentPythonSession()
   >>> session.start()
   >>> 
   >>> # Step 1: Define variables
   >>> result = session.execute("x = 10; y = 20")
   >>> 
   >>> # Step 2: Use those variables
   >>> result = session.execute("z = x + y; print(z)")
   >>> print(result['stdout'])  # 30
   >>> 
   >>> session.stop()

   Use with custom Python executable:

   >>> session = PersistentPythonSession(
   ...     python_executable="/path/to/venv/bin/python",
   ...     startup_code="import numpy as np\nimport pandas as pd"
   ... )

   ..
       !! processed by numpydoc !!




.. py:currentmodule:: PersistentPythonSession

Overview
--------

.. tab-set::



   .. tab-item:: Methods

      .. list-table::
          :header-rows: 0
          :widths: auto

          * - :py:attr:`~start`
            - Start the persistent Python session.
          * - :py:attr:`~execute`
            - Execute Python code in the persistent session.
          * - :py:attr:`~stop`
            - Stop the persistent Python session.
          * - :py:attr:`~restart`
            - Restart the persistent Python session.
          * - :py:attr:`~is_running`
            - Check if the session is currently running.



   .. tab-item:: Attributes

      .. list-table::
          :header-rows: 0
          :widths: auto

          * - :py:attr:`~python_executable`
            - 
          * - :py:attr:`~startup_code`
            - 
          * - :py:attr:`~working_directory`
            - 
          * - :py:attr:`~process`
            - 
          * - :py:attr:`~metadata`
            - 



   .. tab-item:: Special methods

      .. list-table::
          :header-rows: 0
          :widths: auto

          * - :py:attr:`~__enter__`
            - Context manager entry.
          * - :py:attr:`~__exit__`
            - Context manager exit.




Import detail
-------------

.. code-block:: python

    from src.ansys.common.mcp.helpers import PersistentPythonSession


Attribute detail
----------------

.. py:attribute:: python_executable
   :value: 'C:\\repositories\\ansys\\pyansys-common-mcp\\.venv\\Scripts\\python.exe'


.. py:attribute:: startup_code
   :value: None


.. py:attribute:: working_directory
   :value: None


.. py:attribute:: process
   :type:  Optional[subprocess.Popen]
   :value: None


.. py:attribute:: metadata
   :type:  dict[str, Any]



Method detail
-------------

.. py:method:: start() -> dict[str, Any]

   
   Start the persistent Python session.





   :Returns:

       :class:`python:dict`\[:class:`python:str`, :obj:`Any`]
           Dictionary with success status and any startup messages.











   ..
       !! processed by numpydoc !!

.. py:method:: execute(code: str, timeout: float = 30.0) -> dict[str, Any]

   
   Execute Python code in the persistent session.


   :Parameters:

       **code** : :class:`python:str`
           Python code to execute.

       **timeout** : :class:`python:float`
           Maximum execution time in seconds (default: 30.0).



   :Returns:

       :class:`python:dict`\[:class:`python:str`, :obj:`Any`]
           Dictionary containing:
           - 'success': bool indicating if execution succeeded
           - 'stdout': str with standard output
           - 'stderr': str with standard error
           - 'error': str with error message (if execution failed)











   ..
       !! processed by numpydoc !!

.. py:method:: stop() -> dict[str, Any]

   
   Stop the persistent Python session.





   :Returns:

       :class:`python:dict`\[:class:`python:str`, :obj:`Any`]
           Dictionary with success status and cleanup messages.











   ..
       !! processed by numpydoc !!

.. py:method:: restart() -> dict[str, Any]

   
   Restart the persistent Python session.

   Stops the current session (if running) and starts a new one.
   All session state (variables, imports) will be lost except
   what's recreated by startup_code.

   This method is intended for manual restarts only, for example when
   the session becomes unresponsive or when you want to reset the state.
   Command history and other application state should be managed at the
   application context level, not in the session itself.




   :Returns:

       :class:`python:dict`\[:class:`python:str`, :obj:`Any`]
           Dictionary with success status and restart messages.








   .. rubric:: Notes

   - This is a manual operation - automatic restart on crashes is NOT implemented
   - Session state is lost (variables, non-startup imports, etc.)
   - The startup_code is re-executed on restart
   - Consider managing command_history at the context level for replay capability


   .. rubric:: Examples

   Basic restart:

   >>> session = PersistentPythonSession()
   >>> session.start()
   >>> # ... do some work ...
   >>> result = session.restart()
   >>> if result["success"]:
   ...     print("Session restarted")

   In an MCP tool with command replay:

   >>> # Get context
   >>> ctx = get_context()
   >>> app_context = ctx.fastmcp._lifespan_result
   >>> 
   >>> # Restart session
   >>> restart_result = app_context.python_session.restart()
   >>> 
   >>> # Optionally replay command history
   >>> if restart_result["success"] and app_context.command_history:
   ...     for cmd in app_context.command_history:
   ...         app_context.python_session.execute(cmd)

   ..
       !! processed by numpydoc !!

.. py:method:: is_running() -> bool

   
   Check if the session is currently running.





   :Returns:

       :ref:`bool <python:bltin-boolean-values>`
           True if session is running, False otherwise.











   ..
       !! processed by numpydoc !!

.. py:method:: __enter__()

   
   Context manager entry.
















   ..
       !! processed by numpydoc !!

.. py:method:: __exit__(exc_type, exc_val, exc_tb)

   
   Context manager exit.
















   ..
       !! processed by numpydoc !!




