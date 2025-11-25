"""Base MCP server infrastructure for PyAnsys libraries.

This module provides the BaseMCPServer class that product-specific MCP
servers can extend to create their own MCP implementations.
"""

from mcp import FastMCP
from typing import Optional
from contextlib import asynccontextmanager
from ansys.common.mcp.context import PyAnsysBaseAppContext
import logging
from ansys.common.mcp.helpers import PersistentPythonSession


logger = logging.getLogger(__name__)

class PyAnsysBaseMCP(FastMCP):
    def __init__(self, python_executable: Optional[str] = None, *args, **kwargs):
        """
        Base MCP server for PyAnsys libraries.

        Parameters
        ----------
        product_name : str
            Name of the PyAnsys library.
        python_executable : Optional[str]
            Path to the Python executable to use for running the generated code.
            If None, uses the current Python interpreter (sys.executable).
        """
        self.python_executable = python_executable
        super().__init__(*args, **kwargs)

    def product_cleanup(self):
        """
        Cleanup routine before shutting down the server.
        """
        raise NotImplementedError("``product_cleanup`` method must be implemented by subclass")

    def product_startup(self):
        """
        Startup routine to initialize resources when the server starts.
        """
        raise NotImplementedError("``product_startup`` method must be implemented by subclass")

    def start_python_session(self):
        """
        Start a persistent Python session for executing generated code.
        """
        logger.info("Server initialized")
        if self.context.python_executable:
            logger.info(f"Using Python executable: {self.context.python_executable}")
        
        # Start the persistent session
        start_result = self.context.python_session.start()
        if start_result["success"]:
            logger.info("Persistent Python session started")
            logger.info(f"Startup output: {start_result.get('stdout', '')}")
        else:
            logger.warning(f"Failed to start Python session: {start_result.get('error')}")
         
    def cleanup_python_session(self):
        """
        Cleanup the persistent Python session.
        """
        if self.context.python_session and self.context.python_session.is_running():
            try:
                logger.info("Stopping persistent Python session...")
                self.context.python_session.stop()
                logger.info("Persistent Python session stopped")
            except Exception as e:
                logger.error(f"Error stopping Python session: {e}")
    
    @asynccontextmanager
    async def product_lifespan(self):
        """Manage the server's lifecycle with startup and cleanup."""

        context = PyAnsysBaseAppContext(
            python_executable=self.python_executable,
            python_session = PersistentPythonSession(
                python_executable=self.python_executable
            ),
            command_history = [],
        )
        self.context = context
        try:
            self.start_python_session()
            self.product_startup()

            yield self.context

        finally:
            self.cleanup_python_session()
            self.product_cleanup()

