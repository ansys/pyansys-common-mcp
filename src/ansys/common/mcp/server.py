"""Base MCP server infrastructure for PyAnsys libraries.

This module provides the PyAnsysBaseMCP class that product-specific MCP
servers can extend to create their own MCP implementations.
"""

from abc import ABC, abstractmethod
from fastmcp import FastMCP
from typing import Callable, Optional, AsyncIterator
from contextlib import asynccontextmanager
from ansys.common.mcp.context import PyAnsysBaseAppContext
import logging
from ansys.common.mcp.helpers import PersistentPythonSession, logger
from ansys.common.mcp.logging_config import setup_logging


class PyAnsysBaseMCP(FastMCP, ABC):
    def __init__(self, 
                 python_executable: Optional[str] = None,
                 working_directory: Optional[str] = None,
                 *args, 
                 **kwargs
    ):
        """
        PyAnsys Base MCP server for PyAnsys libraries.

        Parameters
        ----------
        python_executable : Optional[str]
            Path to the Python executable to use for running the generated code.
            If None, uses the current Python interpreter (sys.executable).
        working_directory : Optional[str]
            The working directory to use for the Python session.
        """
        # Store parameters before calling super().__init__
        self.python_executable = python_executable
        self.working_directory = working_directory
        
        super().__init__(*args, lifespan=self.product_lifespan, **kwargs)

    @abstractmethod
    def product_cleanup(self):
        """
        Cleanup routine before shutting down the server.
        
        Must be implemented by subclasses to handle product-specific cleanup.
        """
        pass

    @abstractmethod
    def product_startup(self):
        """
        Startup routine to initialize resources when the server starts.
        
        Must be implemented by subclasses to handle product-specific initialization.
        """
        pass
    
    def create_context(self) -> PyAnsysBaseAppContext:
        """Factory method for creating product-specific context.
        
        Override this method in subclasses to return custom context types
        (e.g., PyMAPDLContext with a mapdl field).
        
        Returns
        -------
        PyAnsysBaseAppContext
            The context instance for this server. Default implementation
            creates a base context with Python session support.
            
        Examples
        --------
        Override in a product-specific server:
        
        >>> class PyMAPDLMCP(PyAnsysBaseMCP):
        ...     def create_context(self) -> PyMAPDLContext:
        ...         return PyMAPDLContext(
        ...             python_session=PersistentPythonSession(self.python_executable),
        ...             command_history=[],
        ...         )
        """
        startup_code = """
import matplotlib
# Use non-interactive backend to prevent blocking on plot displays
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import pyvista as pv
import base64
from io import BytesIO
from PIL import Image

# Enable off-screen rendering globally
pv.OFF_SCREEN = True

# Set a clean default theme
pv.set_plot_theme('document')

def save_plot(plotter, filename='plot.png', return_base64=False):
    '''
    Save PyVista plot to file and optionally return as base64.
    
    Parameters
    ----------
    plotter : pv.Plotter
        The PyVista plotter to save
    filename : str
        Output filename
    return_base64 : bool
        If True, return base64-encoded image data
    
    Returns
    -------
    str
        File path or base64 data URI
    '''
    if return_base64:
        img_array = plotter.screenshot(return_img=True, transparent_background=False)
        plotter.close()
        
        img = Image.fromarray(img_array)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
    else:
        plotter.screenshot(filename, transparent_background=False)
        plotter.close()
        return f"Plot saved to {filename}"

def save_matplotlib_plot(filename='plot.png', return_base64=False, dpi=150):
    '''
    Save matplotlib plot to file and optionally return as base64.
    Uses the current matplotlib figure.
    
    Parameters
    ----------
    filename : str
        Output filename
    return_base64 : bool
        If True, return base64-encoded image data
    dpi : int
        Resolution in dots per inch
    
    Returns
    -------
    str
        File path or base64 data URI
    '''
    if return_base64:
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
    else:
        plt.savefig(filename, dpi=dpi, bbox_inches='tight')
        plt.close()
        return f"Plot saved to {filename}"

# Print confirmation
print("Matplotlib configured with non-interactive backend (Agg)")
print("PyVista configured for off-screen rendering")
"""
        python_session=PersistentPythonSession(
            python_executable=self.python_executable,
            working_directory=self.working_directory,
            startup_code=startup_code
        )
        return PyAnsysBaseAppContext(
            python_session=python_session,
            command_history=[],
        )

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
    async def product_lifespan(self, server: FastMCP) -> AsyncIterator[PyAnsysBaseAppContext]:
        """Default lifespan for PyAnsys MCP servers.

        Product-specific servers can override this method if needed.

        Parameters
        ----------
        server : FastMCP
            The MCP server instance.
        
        Yields
        ------
        AsyncIterator[PyAnsysBaseAppContext]
            The application context for the MCP server.
        
        Notes
        -----
        This method orchestrates the complete lifecycle:
        1. Creates context (via factory method - extensible by subclasses)
        2. Initializes Python session (managed by base class)
        3. Calls product-specific startup
        4. Yields context to the application
        5. Cleans up in reverse order on shutdown
        """
        # Use factory method to create context (subclasses can override)
        self.server = server
        self.context = self.create_context()
        
        try:
            self.start_python_session()
            self.product_startup()

            yield self.context

        finally:
            self.cleanup_python_session()
            self.product_cleanup()

