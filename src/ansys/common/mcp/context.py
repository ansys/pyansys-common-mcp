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
        The connected Ansys product instance. Using Any to support
        different product types without strict type coupling.
    metadata : dict
        Additional context data that products may need to store.
    python_executable : Optional[str]
        Path to the Python executable used for running generated code.
    python_session : Optional[Any]
        An instance of PersistentPythonSession for managing a persistent
        Python session.

    Examples
    --------
    Extend the base context for a specific product:

    >>> from ansys.common.mcp import BaseAppContext
    >>> from dataclasses import dataclass
    >>> from typing import Optional
    >>> 
    >>> @dataclass
    >>> class MAPDLAppContext(BaseAppContext):
    ...     mapdl: Optional[Any] = None
    ...     
    ...     @property
    ...     def product_instance(self):
    ...         return self.mapdl
    """

    product_instance: Optional[Any] = None
    python_executable: Optional[str] = None
    python_session: Optional[Any] = None  # PersistentPythonSession instance
    metadata: dict = field(default_factory=dict)
    command_history: list = field(default_factory=list)
