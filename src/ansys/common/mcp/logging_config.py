# Copyright (C) 2025 - 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Logging configuration for PyAnsys MCP servers.

This module provides centralized logging configuration that ensures
log messages are properly routed to stderr (not stdout) to avoid
interfering with the MCP protocol on stdio transport.
"""

import logging
import os
import sys
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Configure logging for MCP servers.

    Sets up logging to stderr (to avoid interfering with MCP protocol on stdout)
    and optionally to a file. The log level can be controlled via the LOGLEVEL
    environment variable or the level parameter.

    Parameters
    ----------
    level : Optional[str]
        Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        If None, uses LOGLEVEL environment variable or defaults to INFO.
    log_file : Optional[str]
        Optional path to log file. If provided, logs will be written to both
        stderr and the file.
    format_string : Optional[str]
        Custom format string for log messages. If None, uses a default format.

    Returns
    -------
    logging.Logger
        The root logger instance

    Examples
    --------
    Basic setup (logs to stderr):

    >>> from ansys.common.mcp.logging_config import setup_logging
    >>> logger = setup_logging()
    >>> logger.info("Server starting...")

    With file output:

    >>> logger = setup_logging(level="DEBUG", log_file="server.log")

    Using environment variable:

    >>> # Set LOGLEVEL=DEBUG before running
    >>> logger = setup_logging()

    Notes
    -----
    - Logs are sent to stderr, NOT stdout (stdout is reserved for MCP protocol)
    - If logs went to stdout, it would break the MCP protocol and cause client communication to fail
    - The LOGLEVEL environment variable can be used to set the log level
    - The root logger is configured, so all loggers in your application will use this config
    """
    # Determine log level
    if level is None:
        level = os.getenv("LOGLEVEL", "INFO").upper()
    else:
        level = level.upper()

    # Validate log level
    numeric_level = getattr(logging, level, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Default format string
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Stderr handler (always present)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(numeric_level)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)

    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            root_logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            root_logger.warning(f"Failed to setup file logging to {log_file}: {e}")

    root_logger.debug(f"Logging configured at level: {level}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    This is a convenience wrapper around logging.getLogger() that ensures
    logging has been configured. If setup_logging() hasn't been called,
    it will be called with default settings.

    Parameters
    ----------
    name : str
        Logger name (typically __name__ of the calling module)

    Returns
    -------
    logging.Logger
        Logger instance

    Examples
    --------
    >>> from ansys.common.mcp.logging_config import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Processing request...")
    """
    # Check if root logger has handlers
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # Setup with defaults if not already configured
        setup_logging()

    return logging.getLogger(name)
