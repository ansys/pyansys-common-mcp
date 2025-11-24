"""Base MCP server infrastructure for PyAnsys libraries.

This module provides the BaseMCPServer class that product-specific MCP
servers can extend to create their own MCP implementations.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


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
    """

    product_instance: Optional[Any] = None
    metadata: dict = None

    def __post_init__(self):
        """Initialize metadata dict if not provided."""
        if self.metadata is None:
            self.metadata = {}


class BaseMCPServer:
    """Base class for PyAnsys MCP servers.

    This class provides common infrastructure for MCP servers across
    PyAnsys libraries. Product-specific servers should inherit from
    this class and implement their own tools and lifecycle management.

    Parameters
    ----------
    product_name : str
        Name of the Ansys product (e.g., "PyMAPDL", "PyFluent").
    lifespan_func : Optional[Callable]
        Optional custom lifespan context manager. If not provided,
        a default lifespan will be used.

    Attributes
    ----------
    mcp : FastMCP
        The FastMCP server instance that handles the MCP protocol.
    product_name : str
        Name of the Ansys product this server supports.

    Examples
    --------
    Create a product-specific MCP server:

    >>> from ansys.common.mcp import BaseMCPServer, BaseAppContext
    >>> 
    >>> class MAPDLServer(BaseMCPServer):
    ...     def __init__(self):
    ...         super().__init__("PyMAPDL")
    ...         self._register_mapdl_tools()
    ...     
    ...     def _register_mapdl_tools(self):
    ...         @self.mcp.tool()
    ...         def launch_mapdl(ctx):
    ...             # MAPDL-specific implementation
    ...             pass
    """

    def __init__(
        self,
        product_name: str,
        lifespan_func: Optional[Callable[..., AsyncIterator[BaseAppContext]]] = None,
    ):
        """Initialize the base MCP server.

        Parameters
        ----------
        product_name : str
            Name of the Ansys product.
        lifespan_func : Optional[Callable]
            Custom lifespan context manager for the server.
        """
        self.product_name = product_name

        # Use provided lifespan or create a default one
        if lifespan_func is None:
            lifespan_func = self._default_lifespan

        self.mcp = FastMCP(product_name, lifespan=lifespan_func)
        logger.info(f"Initialized {product_name} MCP Server")

    @asynccontextmanager
    async def _default_lifespan(self, server: FastMCP) -> AsyncIterator[BaseAppContext]:
        """Default lifespan context manager.

        Products can override this by passing their own lifespan_func
        during initialization.

        Parameters
        ----------
        server : FastMCP
            The FastMCP server instance.

        Yields
        ------
        BaseAppContext
            Application context for the server lifecycle.
        """
        context = BaseAppContext()
        try:
            logger.info(
                f"{self.product_name} MCP Server initialized. "
                f"Ready to accept connections."
            )
            yield context
        finally:
            # Cleanup on shutdown
            if context.product_instance is not None:
                try:
                    logger.info(f"Cleaning up {self.product_name} connection...")
                    # Attempt graceful cleanup
                    if hasattr(context.product_instance, "exit"):
                        context.product_instance.exit()
                    logger.info(f"{self.product_name} cleanup complete")
                except Exception as e:
                    logger.error(f"Error during {self.product_name} cleanup: {e}")

    def run(self):
        """Run the MCP server.

        This is the main entry point that starts the server and listens
        for MCP protocol messages via stdio.
        """
        import asyncio

        logger.info(f"Starting {self.product_name} MCP Server...")
        asyncio.run(self.mcp.run_stdio_async())


def create_mcp_server(
    product_name: str,
    lifespan_func: Optional[Callable[..., AsyncIterator[BaseAppContext]]] = None,
) -> FastMCP:
    """Factory function to create an MCP server instance.

    This is a convenience function for products that prefer a functional
    approach over class inheritance.

    Parameters
    ----------
    product_name : str
        Name of the Ansys product.
    lifespan_func : Optional[Callable]
        Custom lifespan context manager.

    Returns
    -------
    FastMCP
        Configured FastMCP server instance ready for tool registration.

    Examples
    --------
    Create a server using the factory function:

    >>> from ansys.common.mcp import create_mcp_server
    >>> 
    >>> mcp = create_mcp_server("PyFluent", lifespan=my_lifespan)
    >>> 
    >>> @mcp.tool()
    >>> def my_tool():
    ...     pass
    """
    server = BaseMCPServer(product_name, lifespan_func)
    return server.mcp
