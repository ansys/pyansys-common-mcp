"""Common context definitions for PyAnsys MCP servers.

This module provides base context classes that can be extended by
product-specific MCP implementations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["BaseAppContext"]


@dataclass
class BaseAppContext:
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
    metadata: dict = field(default_factory=dict)
