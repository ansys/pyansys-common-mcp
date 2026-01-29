





The ``logging_config.py`` module
================================

.. py:module:: src.ansys.common.mcp.logging_config


Summary
-------








.. py:currentmodule:: logging_config
.. tab-set::







    .. tab-item:: Functions

        .. list-table::
          :header-rows: 0
          :widths: auto


          * - :py:obj:`~setup_logging`
            - Configure logging for MCP servers.


          * - :py:obj:`~get_logger`
            - Get a logger instance with the specified name.

















Description
-----------

Logging configuration for PyAnsys MCP servers.

This module provides centralized logging configuration that ensures
log messages are properly routed to stderr (not stdout) to avoid
interfering with the MCP protocol on stdio transport.

..
    !! processed by numpydoc !!






Module detail
-------------

.. py:function:: setup_logging(level: Optional[str] = None, log_file: Optional[str] = None, format_string: Optional[str] = None) -> logging.Logger


   Configure logging for MCP servers.

   Sets up logging to stderr (to avoid interfering with MCP protocol on stdout)
   and optionally to a file. The log level can be controlled via the LOGLEVEL
   environment variable or the level parameter.

   :Parameters:

       **level** : :obj:`Optional`\[:class:`python:str`]
           Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
           If None, uses LOGLEVEL environment variable or defaults to INFO.

       **log_file** : :obj:`Optional`\[:class:`python:str`]
           Optional path to log file. If provided, logs will be written to both
           stderr and the file.

       **format_string** : :obj:`Optional`\[:class:`python:str`]
           Custom format string for log messages. If None, uses a default format.



   :Returns:

       :obj:`logging.Logger`
           The root logger instance








   .. rubric:: Notes

   - Logs are sent to stderr, NOT stdout (stdout is reserved for MCP protocol)
   - The LOGLEVEL environment variable can be used to set the log level
   - The root logger is configured, so all loggers in your application will use this config


   .. rubric:: Examples

   Basic setup (logs to stderr):

   >>> from ansys.common.mcp.logging_config import setup_logging
   >>> logger = setup_logging()
   >>> logger.info("Server starting...")

   With file output:

   >>> logger = setup_logging(level="DEBUG", log_file="server.log")

   Using environment variable:

   >>> # Set LOGLEVEL=DEBUG before running
   >>> logger = setup_logging()

   ..
       !! processed by numpydoc !!

.. py:function:: get_logger(name: str) -> logging.Logger


   Get a logger instance with the specified name.

   This is a convenience wrapper around logging.getLogger() that ensures
   logging has been configured. If setup_logging() hasn't been called,
   it will be called with default settings.

   :Parameters:

       **name** : :class:`python:str`
           Logger name (typically __name__ of the calling module)



   :Returns:

       :obj:`logging.Logger`
           Logger instance










   .. rubric:: Examples

   >>> from ansys.common.mcp.logging_config import get_logger
   >>> logger = get_logger(__name__)
   >>> logger.info("Processing request...")

   ..
       !! processed by numpydoc !!
