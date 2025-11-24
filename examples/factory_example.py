"""Example: Using the factory function approach.

This example shows an alternative, more functional approach to
creating an MCP server using the create_mcp_server factory function.
"""

from ansys.common.mcp import create_mcp_server, BaseAppContext
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

logger = logging.getLogger(__name__)


# Step 1: Define the lifespan function
@asynccontextmanager
async def my_product_lifespan(server) -> AsyncIterator[BaseAppContext]:
    """Manage product lifecycle."""
    context = BaseAppContext()
    try:
        logger.info("Product initialized")
        yield context
    finally:
        if context.product_instance is not None:
            logger.info("Cleaning up...")
            # Add cleanup logic


# Step 2: Create the MCP server using the factory
mcp = create_mcp_server("MyProduct", lifespan_func=my_product_lifespan)


# Step 3: Register tools using decorators
@mcp.tool()
def hello_world() -> str:
    """Simple hello world tool."""
    return "Hello from MyProduct MCP!"


@mcp.tool()
def add_numbers(a: int, b: int) -> str:
    """Add two numbers.
    
    Parameters
    ----------
    a : int
        First number
    b : int
        Second number
        
    Returns
    -------
    str
        Result message
    """
    result = a + b
    return f"{a} + {b} = {result}"


@mcp.tool()
def connect(ctx, host: str = "localhost") -> str:
    """Connect to the product.
    
    Parameters
    ----------
    ctx : Context
        MCP context
    host : str
        Host to connect to
        
    Returns
    -------
    str
        Connection status
    """
    # Simulate connection
    connection = {"host": host, "status": "connected"}
    ctx.request_context.lifespan_context.product_instance = connection
    return f"Connected to {host}"


# Step 4: Run the server
def main():
    """Main entry point."""
    import asyncio
    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
