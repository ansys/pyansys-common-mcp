"""Example: Creating a minimal PyAnsys MCP Server.

This example demonstrates how to use ansys-common-mcp to create
a simple MCP server for a PyAnsys product.
"""

from ansys.common.mcp import BaseMCPServer, BaseAppContext
from dataclasses import dataclass
from typing import Optional, Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

logger = logging.getLogger(__name__)


# Step 1: Create a product-specific context (optional but recommended)
@dataclass
class ExampleProductContext(BaseAppContext):
    """Context for our example product.
    
    This extends BaseAppContext to add product-specific fields.
    """
    session_data: dict = None
    
    def __post_init__(self):
        """Initialize session data."""
        if self.session_data is None:
            self.session_data = {}
        # Call parent __post_init__ if it exists
        if hasattr(super(), '__post_init__'):
            super().__post_init__()


# Step 2: Create the MCP server class
class ExampleProductServer(BaseMCPServer):
    """Example MCP server for a PyAnsys product.
    
    This demonstrates the recommended pattern for creating a
    product-specific MCP server.
    """
    
    def __init__(self):
        """Initialize the example product server."""
        # Initialize with custom lifespan
        super().__init__(
            product_name="ExampleProduct",
            lifespan_func=self.product_lifespan
        )
        
        # Register our tools
        self._register_tools()
    
    @asynccontextmanager
    async def product_lifespan(self, server) -> AsyncIterator[ExampleProductContext]:
        """Manage the product lifecycle.
        
        This is where you handle initialization and cleanup of
        product-specific resources.
        """
        context = ExampleProductContext()
        try:
            logger.info("Example Product MCP Server initialized")
            yield context
        finally:
            # Cleanup
            if context.connection is not None:
                try:
                    logger.info("Cleaning up connection...")
                    # Add your cleanup logic here
                    # context.connection.close()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
    
    def _register_tools(self):
        """Register all MCP tools for this product."""
        
        @self.mcp.tool()
        def connect_to_product(ctx, host: str = "localhost", port: int = 50052) -> str:
            """Connect to the example product.
            
            Parameters
            ----------
            ctx : Context
                MCP context
            host : str
                Host address
            port : int
                Port number
                
            Returns
            -------
            str
                Connection status message
            """
            logger.info(f"Connecting to {host}:{port}...")
            
            # Check if already connected
            if ctx.request_context.lifespan_context.product_instance is not None:
                return f"Already connected to {host}:{port}"
            
            try:
                # Add your connection logic here
                # connection = YourProduct.connect(host=host, port=port)
                
                # For this example, we'll simulate a connection
                connection = {"host": host, "port": port, "status": "connected"}
                
                # Store in context
                ctx.request_context.lifespan_context.product_instance = connection
                
                return f"Successfully connected to {host}:{port}"
            
            except Exception as e:
                error_msg = f"Failed to connect: {str(e)}"
                logger.error(error_msg)
                return error_msg
        
        @self.mcp.tool()
        def disconnect_from_product(ctx) -> str:
            """Disconnect from the example product.
            
            Parameters
            ----------
            ctx : Context
                MCP context
                
            Returns
            -------
            str
                Disconnection status message
            """
            connection = ctx.request_context.lifespan_context.product_instance
            
            if connection is None:
                return "No active connection to disconnect"
            
            try:
                logger.info("Disconnecting...")
                
                # Add your disconnection logic here
                # connection.close()
                
                # Clear from context
                ctx.request_context.lifespan_context.product_instance = None
                
                return "Successfully disconnected"
            
            except Exception as e:
                error_msg = f"Error during disconnect: {str(e)}"
                logger.error(error_msg)
                return error_msg
        
        @self.mcp.tool()
        def check_status(ctx) -> str:
            """Check connection status.
            
            Parameters
            ----------
            ctx : Context
                MCP context
                
            Returns
            -------
            str
                Status message
            """
            connection = ctx.request_context.lifespan_context.product_instance
            
            if connection is None:
                return "Not connected. Use connect_to_product to establish a connection."
            
            # Add your status check logic here
            return f"Connected: {connection}"
        
        @self.mcp.tool()
        def run_command(ctx, command: str) -> str:
            """Run a command on the product.
            
            Parameters
            ----------
            ctx : Context
                MCP context
            command : str
                Command to execute
                
            Returns
            -------
            str
                Command result
            """
            connection = ctx.request_context.lifespan_context.product_instance
            
            if connection is None:
                return "Not connected. Use connect_to_product first."
            
            try:
                logger.info(f"Executing command: {command}")
                
                # Add your command execution logic here
                # result = connection.execute(command)
                
                # For this example, simulate execution
                result = f"Executed: {command}"
                
                return result
            
            except Exception as e:
                error_msg = f"Error executing command: {str(e)}"
                logger.error(error_msg)
                return error_msg


# Step 3: Create the main entry point
def main():
    """Main entry point for the MCP server."""
    server = ExampleProductServer()
    server.run()


if __name__ == "__main__":
    main()
