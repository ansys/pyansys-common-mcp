# ansys-common-mcp

Common Model Context Protocol (MCP) infrastructure for PyAnsys libraries.

## Overview

This package provides base classes, utilities, and common tools that PyAnsys product-specific MCP servers can extend and use. It enables consistent MCP server implementations across the PyAnsys ecosystem while allowing each product to add its own specialized functionality.

## Purpose

`ansys-common-mcp` serves as a foundation for building MCP servers for Ansys products like:
- **PyMAPDL** ([pymapdl-mcp](https://github.com/ansys/pymapdl-mcp))
- **PyFluent** (future)
- Other PyAnsys libraries

## Features

- **BaseMCPServer**: Base class for creating product-specific MCP servers
- **BaseAppContext**: Common context structure for managing product connections
- **Common Tools**: Reusable tools for environment checking, version validation, etc.
- **Utility Functions**: Helpers for exception handling, logging, and more
- **Consistent API**: Standardized patterns across all PyAnsys MCP implementations

## Installation

### From PyPI (when published)

```bash
pip install ansys-common-mcp
```

### From Source

```bash
git clone https://github.com/ansys-internal/pyansys-common-mcp.git
cd pyansys-common-mcp
pip install -e .
```

## Usage

### For Product Developers

This library is designed to be used by PyAnsys product maintainers to create MCP servers for their specific products.

#### Option 1: Class-Based Approach (Recommended)

```python
# In your product's MCP package (e.g., pymapdl-mcp)
from ansys.common.mcp import BaseMCPServer, BaseAppContext
from dataclasses import dataclass
from typing import Optional

@dataclass
class MAPDLAppContext(BaseAppContext):
    """MAPDL-specific context extending the base."""
    mapdl: Optional[Any] = None
    
    @property
    def product_instance(self):
        return self.mapdl

class MAPDLServer(BaseMCPServer):
    """PyMAPDL MCP Server implementation."""
    
    def __init__(self):
        # Create custom lifespan
        super().__init__("PyMAPDL", lifespan_func=self.mapdl_lifespan)
        self._register_mapdl_tools()
    
    async def mapdl_lifespan(self, server):
        """Custom lifespan for MAPDL connections."""
        context = MAPDLAppContext()
        try:
            yield context
        finally:
            if context.mapdl is not None:
                context.mapdl.exit()
    
    def _register_mapdl_tools(self):
        """Register MAPDL-specific tools."""
        
        @self.mcp.tool()
        def launch_mapdl(ctx, nproc: int = 2):
            """Launch MAPDL instance."""
            from ansys.mapdl.core import launch_mapdl
            mapdl = launch_mapdl(nproc=nproc)
            ctx.request_context.lifespan_context.mapdl = mapdl
            return f"MAPDL launched at {mapdl.ip}:{mapdl.port}"
        
        @self.mcp.tool()
        def run_command(ctx, cmd: str):
            """Run MAPDL command."""
            mapdl = ctx.request_context.lifespan_context.mapdl
            if mapdl is None:
                return "No MAPDL connection"
            return mapdl.run(cmd)

# Entry point
if __name__ == "__main__":
    server = MAPDLServer()
    server.run()
```

#### Option 2: Factory Function Approach

```python
# In your product's MCP package
from ansys.common.mcp import create_mcp_server, BaseAppContext

# Create server with custom lifespan
async def my_lifespan(server):
    context = BaseAppContext()
    try:
        yield context
    finally:
        # Cleanup
        pass

mcp = create_mcp_server("PyFluent", lifespan_func=my_lifespan)

# Register tools directly
@mcp.tool()
def my_tool(ctx):
    """Product-specific tool."""
    pass

# Run the server
if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())
```

### Using Common Tools

The package provides common tools that can be used across all product implementations:

```python
from ansys.common.mcp import check_package_version, get_python_environment_info

# Check if a package is installed
result = check_package_version("ansys-mapdl-core")
print(result)  # "ansys-mapdl-core version: 0.68.3"

# Get environment information
env_info = get_python_environment_info()
print(env_info)
```

### Integrating Common Tools into Your MCP Server

```python
from ansys.common.mcp import BaseMCPServer
from ansys.common.mcp.tools import check_package_version

class MyProductServer(BaseMCPServer):
    def __init__(self):
        super().__init__("MyProduct")
        self._register_common_tools()
        self._register_product_tools()
    
    def _register_common_tools(self):
        """Register common tools as MCP tools."""
        
        @self.mcp.tool()
        def check_version(package_name: str) -> str:
            """Check if a package is installed."""
            return check_package_version(package_name)
```

## Architecture

```
ansys-common-mcp/
├── src/ansys/common/mcp/
│   ├── __init__.py          # Public API exports
│   ├── server.py            # BaseMCPServer class
│   ├── context.py           # BaseAppContext
│   ├── helpers.py           # Utility functions
│   ├── prompts.py           # Common prompts (future)
│   └── tools/               # Common MCP tools
│       ├── __init__.py
│       └── environment.py   # Version/environment tools
```

## Product Integration Pattern

Each PyAnsys product creates its own MCP package that:

1. **Depends on** `ansys-common-mcp` in `pyproject.toml`:
   ```toml
   dependencies = [
       "ansys-common-mcp>=0.1.0",
       "ansys-mapdl-core>=0.68.0",  # Product-specific
   ]
   ```

2. **Extends** the base server:
   - Inherit from `BaseMCPServer`
   - Create product-specific context
   - Register product-specific tools

3. **Provides** entry point in its own package:
   ```toml
   [project.scripts]
   pymapdl-mcp = "ansys.mapdl.mcp.__main__:main"
   ```

## Examples

### Example: PyMAPDL MCP

See the complete implementation at [github.com/ansys/pymapdl-mcp](https://github.com/ansys/pymapdl-mcp)

### Example: Minimal Product Server

```python
# File: ansys/myproduct/mcp/__init__.py
from ansys.common.mcp import BaseMCPServer

class MyProductServer(BaseMCPServer):
    def __init__(self):
        super().__init__("MyProduct")
        
        @self.mcp.tool()
        def hello() -> str:
            """Simple test tool."""
            return "Hello from MyProduct MCP!"

def main():
    server = MyProductServer()
    server.run()

if __name__ == "__main__":
    main()
```

## Development

### Installation for Development

```bash
git clone https://github.com/ansys-internal/pyansys-common-mcp.git
cd pyansys-common-mcp
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

## API Reference

### BaseMCPServer

Base class for creating product-specific MCP servers.

**Methods:**
- `__init__(product_name: str, lifespan_func: Optional[Callable] = None)`
- `run()`: Start the MCP server

### BaseAppContext

Base context for managing product connections.

**Attributes:**
- `product_instance: Optional[Any]`: The connected product instance
- `metadata: dict`: Additional context data

### Common Tools

#### check_package_version(package_name: str) -> str
Check if a package is installed and return its version.

#### get_python_environment_info() -> str
Get comprehensive Python environment information.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [PyMAPDL MCP Server](https://github.com/ansys/pymapdl-mcp)
- [PyAnsys Documentation](https://docs.pyansys.com/)

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/ansys-internal/pyansys-common-mcp/issues)
- Contact the PyAnsys team at pyansys.core@ansys.com
