# PyAnsys Common MCP

[![PyAnsys](https://img.shields.io/badge/Py-Ansys-ffc107.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABDklEQVQ4jWNgoDfg5+OQgMJ/0AqCqXGQMEBAwBEKQj5gGDjQsA80UeCDscxrD4YhGsgABEELnC5zAwAu6ADCKQDAQzNBFwAAVdgFEAnfDiQAATyIBaAFgCbkAI5DQwAVGAYkAMA4gHgg2AC+AAgQIABggagAqyAD4AF0MaB8gCbgoEAL0MEYRz4WxpMdWFzQBYKhK8DjEYH9KDgAw9ACAAgwFCgC2AMJvgAAJv+LQQJwJ8AAKQEoAAxr7W4AG/wGqAB4AACkR7cEdcEBQOPjIvAEtRDoAbYLANQAZGsBEAFeBwCsAY0HgGCAAEQTaDj7xQAABItJ+S3DsQAAAABJRU5ErkJggg==)](https://docs.pyansys.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Common infrastructure for building [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers for PyAnsys libraries.

## Overview

This package provides the foundation for creating MCP servers that enable AI assistants (like Claude, ChatGPT) to interact with Ansys products through PyAnsys libraries. 

**Key Features:**
- 🐍 **Persistent Python sessions** - Stateful code execution across multiple AI requests
- ♻️ **Lifecycle management** - Automatic startup, cleanup, and error handling
- 🏗️ **Extensible architecture** - Base classes and patterns for product-specific implementations
- 📝 **Logging infrastructure** - Pre-configured logging that doesn't interfere with MCP protocol

## Installation

```bash
pip install ansys-common-mcp
```

For development:
```bash
pip install ansys-common-mcp[dev]
```

## Quick Start

Creating an MCP server for your PyAnsys library involves three main steps:

1. **Define your custom context** - Extend `PyAnsysBaseAppContext` to store product-specific state
2. **Implement your MCP server** - Extend `PyAnsysBaseMCP` with startup/cleanup logic
3. **Create MCP tools** - Define tools that interact with your product

### Complete Minimal Example

Here's a minimal MCP server for a hypothetical PyAnsys library:

### Step 2: Define Your Custom Context

Create `context.py` to add product-specific fields:

```python
# src/pymapdl_mcp/context.py
from dataclasses import dataclass
**1. Define Custom Context** (`context.py`)

```python
from dataclasses import dataclass
from typing import Optional
from ansys.common.mcp import PyAnsysBaseAppContext

@dataclass
class MyProductContext(PyAnsysBaseAppContext):
    """Context for MyProduct MCP server."""
    product_instance: Optional[Any] = None  # Your product connection
```

**2. Implement MCP Server** (`server.py`)

```python
from ansys.common.mcp import PyAnsysBaseMCP, PersistentPythonSession
from my_product_mcp.context import MyProductContext
from my_product import connect  # Your product's API

class MyProductMCP(PyAnsysBaseMCP):
    """MCP Server for MyProduct."""
    
    def create_context(self) -> MyProductContext:
        """Create product-specific context."""
        return MyProductContext(
            python_session=PersistentPythonSession(
                python_executable=self.python_executable,
                working_directory=self.working_directory,
            ),
            command_history=[],
        )
    
    def product_startup(self):
        """Initialize product connection."""
        self.context.product_instance = connect()
    
    def product_cleanup(self):
        """Clean up product connection."""
        if self.context.product_instance:
            self.context.product_instance.disconnect()
```

**3. Create MCP Tools** (`tools.py`)

```python
from fastmcp.server.dependencies import get_context

def register_tools(mcp):
    """Register product-specific tools."""
    
    @mcp.tool()
    def execute_command(command: str) -> str:
        """Execute a product command.
        
        Parameters
        ----------
        command : str
            Command to execute
            
        Returns
        -------
        str
            Command result
        """
        ctx = get_context()
        app_context = ctx.fastmcp._lifespan_result
        
        result = app_context.product_instance.run(command)
        app_context.command_history.append(command)
        return result
```

**4. Wire It Together** (`__main__.py`)

```python
from my_product_mcp import MyProductMCP, register_tools

def main():
    mcp = MyProductMCP(name="my-product-mcp")
    register_tools(mcp)
    mcp.run()
    return 0
```

### Running Your
```

## Architecture Overview

```
┌─────────────────────────────────────┐
│   Your Product MCP Server           │
│   (e.g., PyMAPDLMCP)                │
│                                     │
│   ├── create_context() ─────────────┼──> Returns YourContext
│   ├── product_startup() ────────────┼──> launch_mapdl()
│   └── product_cleanup() ────────────┼──> mapdl.exit()
└──────────────┬──────────────────────┘
               │ extends
┌──────────────▼──────────────────────┐
│   PyAnsysBaseMCP (Base Class)       │
│                                     │
│   ├── product_lifespan() ───────────┼──> Manages lifecycle
│   ├── start_python_session() ───────┼──> Starts Python
│   └── cleanup_python_session() ─────┼──> Stops Python
└─────────────────────────────────────┘
```

**What the Base Class Handles:**
- ✅ Python session creation and management
- ✅ Lifecycle orchestration (startup → run → cleanup)
- ✅ Error handling and logging
- ✅ Context injection into tools

**What You Implement:**
- ✅ Custom context with product-specific fields
- ✅ Product connection/initialization logic
- ✅ Product-specific MCP tools
- ✅ Cleanup logic for your product

## Logging

The framework automatically configures logging to output to **stderr** (not stdout, which is reserved for MCP protocol). This ensures log messages don't interfere with the MCP communication.

### Basic Logging

```python
from ansys.common.mcp import setup_logging, get_logger

# Setup logging (done automatically by the framework)
setup_logging(level="INFO")

# Get a logger in your module
logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Configuring Log Level

You can control the log level via environment variable:

```bash
# Windows PowerShell
$env:LOGLEVEL="DEBUG"
python -m pymapdl_mcp

# Linux/Mac
LOGLEVEL=DEBUG python -m pymapdl_mcp
```

Or programmatically in your `__main__.py`:

```python
from ansys.common.mcp import setup_logging

def main():
    # Configure logging before creating server
    setup_logging(
        level="DEBUG",              # Log level
        log_file="server.log"       # Optional: also log to file
    )
    
    # ... rest of your code
```

### Viewing Logs

Logs are output to stderr, so you'll see them in your terminal when running the server. You can redirect them to a file:

```bash
# Windows PowerShell
python -m pymapdl_mcp 2> server.log

# Linux/Mac
python -m pymapdl_mcp 2> server.log
```

## Common Patterns

### Accessing Python Session in Tools

```python
from fastmcp.server.dependencies import get_context

@mcp.tool()
def execute_python_code(code: str) -> str:
    """Execute Python code in the persistent session."""
    # Get context via dependency injection
    ctx = get_context()
    app_context = ctx.fastmcp._lifespan_result
    
    result = app_context.python_session.execute(code)
    if result["success"]:
pip install -e .
python -m my_product_mcp
```

## Core Concepts

### Architecture

The framework follows a clean separation of concerns:

```
┌─────────────────────────────────┐
│  Your Product MCP Server        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • create_context()             │──> Custom context with product state
│  • product_startup()            │──> Initialize product connection
│  • product_cleanup()            │──> Clean up resources
└────────────┬────────────────────┘
             │ extends
┌────────────▼────────────────────┐
│  PyAnsysBaseMCP (Base)          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ✅ Lifecycle orchestration     │
│  ✅ Python session management   │
│  ✅ Error handling & logging    │
│  ✅ Context injection           │
└─────────────────────────────────┘
```

**Division of Responsibilities:**
- **Base Class** handles: Python sessions, lifecycle, logging, MCP protocol
- **Your Server** handles: Product connections, product-specific tools, custom context

### Key Components

1. **Context** (`PyAnsysBaseAppContext`) - Shared state container
   - Stores product instance, Python session, command history
   - Accessible from all MCP tools via dependency injection
   - Extensible via dataclass inheritance

2. **Python Session** (`PersistentPythonSession`) - Stateful code execution
   - Maintains variables/imports across AI interactions
   - Pre-configured with matplotlib and PyVista for off-screen plotting
   - Supports restart with command replay

3. **Lifecycle Management** - Automatic startup/cleanup
   - `product_startup()` → Initialize your product
   - Tools run → AI interacts with your product
   - `product_cleanup()` → Clean shutdown

## Real-World Example

See **[PyMAPDL-MCP](https://github.com/ansys/pymapdl-mcp)** for a complete, production-ready implementation.

## Documentation

Full documentation available at: [https://github.com/ansys/pyansys-common-mcp](https://github.com/ansys/pyansys-common-mcp)**Documentation**: [Full Documentation](https://github.com/ansys/pyansys-common-mcp)
- **Issues**: [GitHub Issues](https://github.com/ansys/pyansys-common-mcp/issues)
- **Email**: pyansys.core@ansys.com
- **Discussions**: [GitHub Discussions](https://github.com/ansys/pyansys-common-mcp/discussions)