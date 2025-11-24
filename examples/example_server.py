"""Example: Creating a minimal PyAnsys MCP Server.

This example demonstrates how to use ansys-common-mcp to create
a simple MCP server for a PyAnsys product.
"""

from ansys.common.mcp import BaseMCPServer, BaseAppContext
from ansys.common.mcp.helpers import PersistentPythonSession
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
    
    def __init__(self, python_executable: Optional[str] = None):
        """Initialize the example product server.
        
        Parameters
        ----------
        python_executable : Optional[str]
            Path to the Python executable to use for running LLM-generated code.
            If None, uses the current Python interpreter (sys.executable).
        """
        self.python_executable = python_executable
        
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
        product-specific resources, including the persistent Python session.
        """
        context = ExampleProductContext()
        # Store the Python executable in context for tools to use
        context.python_executable = self.python_executable
        
        # Initialize persistent Python session
        context.python_session = PersistentPythonSession(
            python_executable=self.python_executable,
            startup_code=None,  # Optional: Add common imports here
        )
        
        try:
            logger.info("Example Product MCP Server initialized")
            if self.python_executable:
                logger.info(f"Using Python executable: {self.python_executable}")
            
            # Start the persistent session
            start_result = context.python_session.start()
            if start_result["success"]:
                logger.info("Persistent Python session started")
            else:
                logger.warning(f"Failed to start Python session: {start_result.get('error')}")
            
            yield context
        finally:
            # Cleanup persistent session
            if context.python_session and context.python_session.is_running():
                try:
                    logger.info("Stopping persistent Python session...")
                    context.python_session.stop()
                except Exception as e:
                    logger.error(f"Error stopping Python session: {e}")
            
            # Cleanup product connection
            if context.product_instance is not None:
                try:
                    logger.info("Cleaning up connection...")
                    # Add your cleanup logic here
                    # context.product_instance.close()
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
        

        @self.mcp.tool()
        def execute_in_persistent_session(ctx, code: str, timeout: int = 30) -> str:
            """Execute Python code in the persistent session, preserving state.
            
            This tool executes code in a single persistent Python process,
            allowing variables, imports, and state to be maintained across
            multiple executions. Perfect for multi-step workflows where each
            step builds on the previous one.
            
            Parameters
            ----------
            ctx : Context
                MCP context
            code : str
                Python code to execute
            timeout : int
                Maximum execution time in seconds (default: 30)
                
            Returns
            -------
            str
                Formatted execution result with stdout, stderr, and status
                
            Examples
            --------
            Step 1: Define variables
            >>> execute_in_persistent_session("x = 10\\ny = 20")
            
            Step 2: Use those variables
            >>> execute_in_persistent_session("print(x + y)")  # Outputs: 30
            """
            session = ctx.request_context.lifespan_context.python_session
            
            if not session:
                return "✗ No persistent Python session available"
            
            if not session.is_running():
                # Try to start the session
                start_result = session.start()
                if not start_result["success"]:
                    return f"✗ Failed to start session: {start_result.get('error')}"
            
            try:
                logger.info("Executing code in persistent session")
                
                # Execute the code in the persistent session
                result = session.execute(code, timeout=timeout)
                
                # Format the result for the LLM
                if result["success"]:
                    output = f"✓ Execution successful\n\n"
                    if result["stdout"]:
                        output += f"Output:\n{result['stdout']}\n"
                    else:
                        output += "(No output)\n"
                else:
                    output = f"✗ Execution failed\n\n"
                    if result["stderr"]:
                        output += f"Error:\n{result['stderr']}\n"
                    if result["error"]:
                        output += f"Details: {result['error']}\n"
                
                return output
            
            except Exception as e:
                error_msg = f"Error executing code in session: {str(e)}"
                logger.error(error_msg)
                return f"✗ {error_msg}"
        
        @self.mcp.tool()
        def reset_python_session(ctx, startup_code: str = "") -> str:
            """Reset the persistent Python session.
            
            This stops the current Python session and starts a new one,
            clearing all variables and state. Optionally run startup code
            to initialize the new session.
            
            Parameters
            ----------
            ctx : Context
                MCP context
            startup_code : str
                Optional Python code to run after resetting (default: "")
                
            Returns
            -------
            str
                Status message indicating success or failure
            """
            session = ctx.request_context.lifespan_context.python_session
            
            if not session:
                return "✗ No persistent Python session available"
            
            try:
                logger.info("Resetting persistent Python session")
                
                # Stop the current session
                if session.is_running():
                    stop_result = session.stop()
                    if not stop_result["success"]:
                        return f"✗ Failed to stop session: {stop_result.get('error')}"
                
                # Update startup code if provided
                if startup_code:
                    session.startup_code = startup_code
                
                # Start a new session
                start_result = session.start()
                if start_result["success"]:
                    return "✓ Python session reset successfully"
                else:
                    return f"✗ Failed to start new session: {start_result.get('error')}"
            
            except Exception as e:
                error_msg = f"Error resetting session: {str(e)}"
                logger.error(error_msg)
                return f"✗ {error_msg}"
        
        @self.mcp.tool()
        def check_python_session_status(ctx) -> str:
            """Check the status of the persistent Python session.
            
            Parameters
            ----------
            ctx : Context
                MCP context
                
            Returns
            -------
            str
                Status information about the session
            """
            session = ctx.request_context.lifespan_context.python_session
            
            if not session:
                return "No persistent Python session configured"
            
            if session.is_running():
                return f"✓ Session is running\nPython: {session.python_executable}"
            else:
                return f"✗ Session is not running\nPython: {session.python_executable}"


# Step 3: Create the main entry point
def main():
    """Main entry point for the MCP server."""
    import sys
    
    # Optional: Parse command line arguments for python_executable
    python_exec = None
    if len(sys.argv) > 1:
        python_exec = sys.argv[1]
        logger.info(f"Using Python executable from command line: {python_exec}")
    
    server = ExampleProductServer(python_executable=python_exec)
    server.run()


if __name__ == "__main__":
    main()
