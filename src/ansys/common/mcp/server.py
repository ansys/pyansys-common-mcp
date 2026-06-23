# Copyright (C) 2025 - 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base MCP server infrastructure for PyAnsys libraries.

This module provides the ``PyAnsysBaseMCP`` class that product-specific MCP
servers can extend to create their own MCP implementations.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastmcp import FastMCP

from ansys.common.mcp.context import PyAnsysBaseAppContext
from ansys.common.mcp.helpers import PersistentPythonSession, logger


class PyAnsysBaseMCP(FastMCP, ABC):
    """Base MCP server for PyAnsys libraries."""

    def __init__(
        self,
        python_executable: Optional[str] = None,
        working_directory: Optional[str] = None,
        *args,
        **kwargs,
    ):  # noqa: D403
        """PyAnsys Base MCP server for PyAnsys libraries.

        Parameters
        ----------
        python_executable : str, default: None
            Path to the Python executable to use for running the generated code.
            If ``None``, the current Python interpreter (sys.executable) is used.
        working_directory : str, default: None
            Working directory to use for the Python session.
        *args : tuple
            Additional positional arguments passed to FastMCP
        **kwargs : dict
            Additional keyword arguments passed to FastMCP

        """
        # Store parameters before calling super().__init__
        self.python_executable = python_executable
        self.working_directory = working_directory
        self._need_python = True

        super().__init__(*args, lifespan=self.product_lifespan, **kwargs)

    @property
    def need_python(self) -> bool:
        """Whether a persistent Python session needs to be started.

        Returns
        -------
        bool
            True if a persistent Python session needs to be started, False otherwise.
        """
        return self._need_python

    @need_python.setter
    def need_python(self, value: bool):
        """Set whether a persistent Python session needs to be started.

        Parameters
        ----------
        value : bool
            True if a persistent Python session needs to be started, False otherwise.
        """
        self._need_python = value

    @abstractmethod
    def product_cleanup(self):
        """Cleanup routine before shutting down the server.

        This abstract method must be implemented by subclasses to handle product-specific cleanup.
        """
        pass

    @abstractmethod
    def product_startup(self):
        """Startup routine to initialize resources when the server starts.

        This abstract method must be implemented by subclasses to handle
        product-specific initialization.
        """
        pass

    def create_context(self) -> PyAnsysBaseAppContext:
        """Create product-specific context.

        Override this method in subclasses to return custom context types
        (such as in ``PyMAPDLContext`` with an MAPDL field).

        Returns
        -------
        PyAnsysBaseAppContext
            Context instance for this server. The default implementation
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
    Save a PyVista plot to file and optionally return as base64.

    Parameters
    ----------
    plotter : pv.Plotter
        PyVista plotter to save
    filename : str, default: ``'plot.png'``
        Output filename
    return_base64 : bool, default: False
        Whether to return base64-encoded image data. If ``False``, saves to file
        and returns file path message.

    Returns
    -------
    str
        File path or base64 data URI.
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
    Save the current Matplotlib plot to file and optionally return as base64.

    Parameters
    ----------
    filename : str, default: ``'plot.png'``
        Output filename.
    return_base64 : bool, default: False
        Whether to return base64-encoded image data. If ``False``, saves to
        file and returns file path message.
    dpi : int, default: 150
        Resolution in dots per inch.

    Returns
    -------
    str
        File path or base64 data URI.
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
print("Matplotlib configured with non-interactive backend (Agg).")
print("PyVista configured for off-screen rendering.")
"""
        python_session = PersistentPythonSession(
            python_executable=self.python_executable,
            working_directory=self.working_directory,
            startup_code=startup_code,
        )
        return PyAnsysBaseAppContext(
            python_session=python_session,
            command_history=[],
        )

    def start_python_session(self):
        """Start a persistent Python session for executing generated code."""
        logger.info("Server initialized.")
        if self.context.python_executable:
            logger.info(f"Using Python executable: {self.context.python_executable}")

        # Start the persistent session
        start_result = self.context.python_session.start()
        if start_result["success"]:
            logger.info("Persistent Python session started.")
            logger.info(f"Startup output: {start_result.get('stdout', '')}")
        else:
            logger.warning(f"Failed to start Python session: {start_result.get('error')}")

    def cleanup_python_session(self):
        """Clean up the persistent Python session."""
        if self.context.python_session and self.context.python_session.is_running():
            try:
                logger.info("Stopping persistent Python session...")
                self.context.python_session.stop()
                logger.info("Persistent Python session stopped.")
            except Exception as e:
                logger.error(f"Error stopping Python session: {e}")

    @asynccontextmanager
    async def product_lifespan(self, server: FastMCP) -> AsyncIterator[PyAnsysBaseAppContext]:
        """Define default lifespan for PyAnsys MCP servers.

        Product-specific servers can override this method if needed.

        Parameters
        ----------
        server : FastMCP
            MCP server instance.

        Yields
        ------
        AsyncIterator[PyAnsysBaseAppContext]
            Application context for the MCP server.

        Notes
        -----
        This method orchestrates the complete lifecycle:
        1. Creates context (via factory method - extensible by subclasses).
        2. Initializes Python session (managed by base class).
        3. Calls product-specific startup.
        4. Yields context to the application.
        5. Cleans up in reverse order on shutdown.

        """
        # Use factory method to create context (subclasses can override)
        self.server = server
        self.context = self.create_context()

        try:
            if self.need_python:
                self.start_python_session()
            self.product_startup()

            yield self.context

        finally:
            if self.need_python:
                self.cleanup_python_session()
            self.product_cleanup()
