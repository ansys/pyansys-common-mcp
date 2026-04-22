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

"""MCP server for PyExample."""

from ansys.common.mcp import PersistentPythonSession, PyAnsysBaseMCP
from ansys.common.mcp.logging_config import get_logger
from pyexample_mcp.context import PyExampleContext

logger = get_logger(__name__)


class PyExampleMCP(PyAnsysBaseMCP):
    """MCP Server for PyExample.

    This server enables AI assistants to interact with PyExample
    for simulation and analysis workflows.
    """

    def __init__(self, launch_mode: str = "local", timeout: int = 60, *args, **kwargs):
        """Initialize PyExample MCP server.

        Parameters
        ----------
        launch_mode : str
            Launch mode for PyExample ('local' or 'remote')
        timeout : int
            Connection timeout in seconds
        *args : tuple
            Additional positional arguments passed to parent class
        **kwargs : dict
            Additional keyword arguments passed to parent class

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

print("PyExample MCP session initialized")
"""

        return PyExampleContext(
            python_session=PersistentPythonSession(
                python_executable=self.python_executable,
                working_directory=self.working_directory,
                startup_code=startup_code,
            ),
            command_history=[],
        )

    def product_startup(self):
        """Launch PyExample instance when server starts.

        This method is called automatically during server startup.
        """
        logger.info(f"Launching PyExample in {self.launch_mode} mode...")

        try:
            # Use the mock PyExample library for testing
            from pyexample_mcp.mock_pyexample import launch_pyexample

            self.context.example_instance = launch_pyexample(
                mode=self.launch_mode, timeout=self.timeout
            )

            logger.info(
                f"PyExample {self.context.example_instance.version} "
                f"launched successfully in {self.launch_mode} mode"
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


# Create the MCP server instance
app = PyExampleMCP(
    name="pyexample-mcp",
)
