# Usage Guide for ansys-common-mcp

This guide provides detailed instructions for PyAnsys product developers on how to use `ansys-common-mcp` to create MCP servers for their products.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Architecture Overview](#architecture-overview)
3. [Creating Your MCP Server](#creating-your-mcp-server)
4. [Testing Your Server](#testing-your-server)
5. [Deployment](#deployment)
6. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Your PyAnsys product package installed
- Basic understanding of async Python and MCP protocol

### Installation

Add `ansys-common-mcp` as a dependency in your product's `pyproject.toml`:

```toml
[project]
dependencies = [
    "ansys-common-mcp>=0.1.0",
    "your-product-package>=1.0.0",
]
```

## Architecture Overview

The `ansys-common-mcp` package provides three main components:

### 1. BaseMCPServer
The base class for creating MCP servers. It handles:
- FastMCP server initialization
- Lifecycle management
- Standard cleanup patterns

### 2. BaseAppContext
A dataclass for storing application state:
- `product_instance`: Your product connection object
- `metadata`: Dictionary for additional data

### 3. Common Tools
Reusable tools available to all products:
- `check_package_version`: Verify installed packages
- `get_python_environment_info`: Get system information

## Creating Your MCP Server

### Step 1: Project Structure

Create your MCP package with this structure:

```
your-product-mcp/
├── src/
│   └── ansys/
│       └── your_product/
│           └── mcp/
│               ├── __init__.py
│               ├── __main__.py
│               ├── server.py
│               └── tools.py
├── tests/
├── pyproject.toml
└── README.md
```

### Step 2: Define Your Context (Optional)

Create a product-specific context in `server.py`:

```python
from ansys.common.mcp import BaseAppContext
from dataclasses import dataclass
from typing import Optional

@dataclass
class YourProductContext(BaseAppContext):
    """Context for your product."""
    your_product: Optional[Any] = None
    
    @property
    def product_instance(self):
        return self.your_product
```

### Step 3: Create Your Server Class

In `server.py`:

```python
from ansys.common.mcp import BaseMCPServer
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

logger = logging.getLogger(__name__)

class YourProductServer(BaseMCPServer):
    """MCP Server for Your Product."""
    
    def __init__(self):
        super().__init__(
            product_name="YourProduct",
            lifespan_func=self.product_lifespan
        )
        self._register_tools()
    
    @asynccontextmanager
    async def product_lifespan(self, server) -> AsyncIterator[YourProductContext]:
        """Manage product lifecycle."""
        context = YourProductContext()
        try:
            logger.info("Server initialized")
            yield context
        finally:
            # Cleanup
            if context.your_product is not None:
                context.your_product.exit()
    
    def _register_tools(self):
        """Register MCP tools."""
        from ansys.your_product.mcp.tools import register_tools
        register_tools(self.mcp)
```

### Step 4: Implement Tools

In `tools.py`:

```python
def register_tools(mcp):
    """Register all product tools."""
    
    @mcp.tool()
    def connect(ctx, host: str = "localhost") -> str:
        """Connect to your product."""
        from your_product import connect as product_connect
        
        instance = product_connect(host=host)
        ctx.request_context.lifespan_context.your_product = instance
        return f"Connected to {host}"
    
    @mcp.tool()
    def run_command(ctx, command: str) -> str:
        """Run a command."""
        instance = ctx.request_context.lifespan_context.your_product
        if instance is None:
            return "Not connected"
        return instance.run(command)
```

### Step 5: Create Entry Points

In `__init__.py`:

```python
from your_product.mcp.server import YourProductServer

__all__ = ["YourProductServer"]
```

In `__main__.py`:

```python
from your_product.mcp.server import YourProductServer

def main():
    server = YourProductServer()
    server.run()

if __name__ == "__main__":
    main()
```

In `pyproject.toml`:

```toml
[project.scripts]
your-product-mcp = "ansys.your_product.mcp.__main__:main"
```

## Testing Your Server

### Unit Tests

Create tests in `tests/test_server.py`:

```python
import pytest
from your_product.mcp.server import YourProductServer

def test_server_creation():
    """Test server can be created."""
    server = YourProductServer()
    assert server.product_name == "YourProduct"
    assert server.mcp is not None

@pytest.mark.asyncio
async def test_lifespan():
    """Test server lifespan."""
    server = YourProductServer()
    async with server.product_lifespan(server.mcp) as context:
        assert context is not None
```

### Integration Tests

Test with a real MCP client:

```python
# Configure your IDE or Claude Desktop with:
{
  "mcpServers": {
    "your-product": {
      "command": "python",
      "args": ["-m", "ansys.your_product.mcp"]
    }
  }
}
```

## Deployment

### Package Distribution

1. Build your package:
   ```bash
   python -m build
   ```

2. Upload to PyPI:
   ```bash
   twine upload dist/*
   ```

### User Installation

Users install your package:
```bash
pip install your-product-mcp
```

Then run:
```bash
your-product-mcp
```

Or configure in their MCP client:
```json
{
  "mcpServers": {
    "your-product": {
      "command": "your-product-mcp"
    }
  }
}
```

## Best Practices

### 1. Error Handling

Always handle exceptions gracefully:

```python
@mcp.tool()
def my_tool(ctx) -> str:
    try:
        # Tool implementation
        return "Success"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"
```

### 2. Logging

Use proper logging levels:

```python
logger.debug("Detailed information")
logger.info("General information")
logger.warning("Warning messages")
logger.error("Error messages")
```

### 3. Documentation

Document all tools with clear docstrings:

```python
@mcp.tool()
def my_tool(param: str) -> str:
    """One-line summary.
    
    Detailed description of what the tool does.
    
    Parameters
    ----------
    param : str
        Description of parameter
        
    Returns
    -------
    str
        Description of return value
    """
```

### 4. Context Management

Always check if context is available:

```python
instance = ctx.request_context.lifespan_context.your_product
if instance is None:
    return "Not connected. Use connect tool first."
```

### 5. Cleanup

Ensure proper cleanup in the lifespan:

```python
finally:
    if context.your_product is not None:
        try:
            context.your_product.exit()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
```

## Examples

See the `examples/` directory for complete working examples:
- `example_server.py`: Full class-based implementation
- `factory_example.py`: Functional factory approach

## Support

For questions or issues:
- Open an issue on GitHub
- Contact pyansys.core@ansys.com
- See PyMAPDL MCP as a reference implementation

## References

- [PyMAPDL MCP](https://github.com/ansys/pymapdl-mcp) - Complete reference implementation
- [MCP Documentation](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
