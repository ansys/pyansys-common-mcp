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
    metadata: dict = field(default_factory=dict)
    command_history: list = field(default_factory=list)
