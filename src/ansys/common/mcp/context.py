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

"""Common context definitions for PyAnsys MCP servers.

This module provides base context classes that can be extended by
product-specific MCP implementations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["PyAnsysBaseAppContext"]


@dataclass
class PyAnsysBaseAppContext:
    """Base application context for PyAnsys MCP servers.

    This provides a common structure that product-specific contexts
    can extend. The product_instance field can hold any Ansys product
    connection (MAPDL, Fluent, Maxwell, etc.).

    Attributes
    ----------
    product_instance : Optional[Any]
        The main product instance (e.g., MAPDL, Fluent) associated with the context.
    python_executable : Optional[Any]
        The Python executable used for the session.
    python_session : Optional[Any]
        An instance of PersistentPythonSession for managing a persistent
        Python session.
    metadata : dict
        A dictionary for storing arbitrary metadata related to the context.
    command_history : list
        A list to keep track of executed commands in the session.

    Examples
    --------
    Extend the base context for a specific product:

    >>> from ansys.common.mcp import PyAnsysBaseAppContext
    >>> from dataclasses import dataclass
    >>> from typing import Optional, Any
    >>>
    >>> @dataclass
    >>> class NewAppContext(PyAnsysBaseAppContext):
    ...     instance: Optional[Any] = None
    ...
    ...     @property
    ...     def product_instance(self):
    ...         return self.instance
    """

    product_instance: Optional[Any] = None
    python_executable: Optional[Any] = None
    python_session: Optional[Any] = None  # PersistentPythonSession instance
    metadata: dict[str, Any] = field(default_factory=dict)
    command_history: list[str] = field(default_factory=list)
