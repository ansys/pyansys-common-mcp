# PyAnsys Common MCP

Common infrastructure for building Model Context Protocol (MCP) servers for PyAnsys libraries.

## What is This?

This package provides the foundation for creating MCP servers that enable AI assistants (like Claude, ChatGPT) to interact with Ansys products through PyAnsys libraries. It handles:

- **Python session management** - Persistent Python environments for code execution
- **Lifecycle management** - Server startup, cleanup, and error handling
- **Extensible architecture** - Base classes for product-specific implementations

## Installation

```bash
pip install ansys-common-mcp
```

For development:
```bash
pip install ansys-common-mcp[dev]
```

## Quick Start: Create Your Product MCP Server

### Step 1: Project Structure

Create a new package for your product (e.g., `pymapdl-mcp`):

```
pymapdl-mcp/
├── pyproject.toml
├── README.md
└── src/
    └── pymapdl_mcp/
        ├── __init__.py
        ├── __main__.py
        ├── server.py       # Your MCP server class
        ├── context.py      # Your custom context
        └── tools.py        # Your MCP tools
```

### Step 2: Define Your Custom Context

Create `context.py` to add product-specific fields:

```python
# src/pymapdl_mcp/context.py
from dataclasses import dataclass
from typing import Optional
from ansys.common.mcp import PyAnsysBaseAppContext

@dataclass
class PyMAPDLContext(PyAnsysBaseAppContext):
    """MAPDL-specific context with mapdl instance."""
    mapdl: Optional[Any] = None  # Your product instance
    project_dir: Optional[str] = None  # Additional fields as needed
```

**Why?** The context holds your product instance and any state that needs to be shared across tools.

### Step 3: Create Your MCP Server

Create `server.py` implementing the three required methods:

```python
# src/pymapdl_mcp/server.py
from ansys.common.mcp import PyAnsysBaseMCP, PersistentPythonSession
from pymapdl_mcp.context import PyMAPDLContext
from pymapdl import launch_mapdl

class PyMAPDLMCP(PyAnsysBaseMCP):
    """MCP Server for PyMAPDL."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up product-specific lifespan
        self.mcp.lifespan = self.product_lifespan

    # REQUIRED: Create your custom context
    def create_context(self) -> PyMAPDLContext:
        """Factory method for creating MAPDL-specific context."""
        return PyMAPDLContext(
            python_executable=self.python_executable,
            python_session=PersistentPythonSession(
                python_executable=self.python_executable,
                working_directory=self.working_directory,
            ),
            command_history=[],
        )

    # REQUIRED: Initialize your product
    def product_startup(self):
        """Launch MAPDL when server starts."""
        self.context.mapdl = launch_mapdl()
        print(f"MAPDL launched: {self.context.mapdl}")

    # REQUIRED: Clean up your product
    def product_cleanup(self):
        """Exit MAPDL when server stops."""
        if self.context.mapdl:
            self.context.mapdl.exit()
            print("MAPDL session closed")
```

**Key Points:**
- `create_context()`: Returns your custom context type
- `product_startup()`: Initialize connections, launch products
- `product_cleanup()`: Close connections, clean up resources
- Python session management is handled automatically by the base class

### Step 4: Add Your MCP Tools

Create `tools.py` with your product-specific MCP tools:

```python
# src/pymapdl_mcp/tools.py
from pymapdl_mcp.server import PyMAPDLMCP
from pymapdl_mcp.context import PyMAPDLContext
from fastmcp.server.dependencies import get_context

def register_tools(mcp: PyMAPDLMCP):
    """Register all MAPDL-specific MCP tools."""

    @mcp.tool()
    def run_mapdl_command(
        command: str
    ) -> str:
        """Execute a MAPDL command.

        Parameters
        ----------
        command : str
            MAPDL command to execute

        Returns
        -------
        str
            Command output
        """
        # Get context via dependency injection
        ctx = get_context()
        app_context = ctx.fastmcp._lifespan_result

        if not app_context.mapdl:
            return "Error: MAPDL not connected"

        result = app_context.mapdl.run(command)
        app_context.command_history.append(command)
        return result

    @mcp.tool()
    def create_geometry(
        geometry_type: str,
        dimensions: dict
    ) -> str:
        """Create geometric entities in MAPDL.

        Parameters
        ----------
        geometry_type : str
            Type of geometry (box, cylinder, sphere)
        dimensions : dict
            Dimensions for the geometry

        Returns
        -------
        str
            Result message
        """
        # Get context via dependency injection
        ctx = get_context()
        app_context = ctx.fastmcp._lifespan_result

        # Your implementation here
        pass
```

**Tool Guidelines:**
- **Do NOT include `ctx` as a function parameter** - it's automatically injected
- Use `get_context()` from `fastmcp.server.dependencies` to access the context
- Access your app context via `ctx.fastmcp._lifespan_result`
- Use type hints for all parameters (except ctx which is internal)
- Write clear docstrings (AI assistants read these!)
- Access product instance via `app_context.mapdl` (or your field name)
- Store relevant info in `app_context.command_history` or `app_context.metadata`

### Step 5: Wire Everything Together

Create `__init__.py`:

```python
# src/pymapdl_mcp/__init__.py
from pymapdl_mcp.server import PyMAPDLMCP
from pymapdl_mcp.context import PyMAPDLContext
from pymapdl_mcp.tools import register_tools

__all__ = ["PyMAPDLMCP", "PyMAPDLContext", "register_tools"]
```

Create `__main__.py` for CLI execution:

```python
# src/pymapdl_mcp/__main__.py
import sys
from pymapdl_mcp import PyMAPDLMCP, register_tools

def main():
    # Initialize your MCP server
    mcp = PyMAPDLMCP(name="pymapdl-mcp")

    # Register your tools
    register_tools(mcp)

    # Run the server
    mcp.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Step 6: Configure pyproject.toml

```toml
[project]
name = "pymapdl-mcp"
version = "0.1.0"
dependencies = [
    "ansys-common-mcp>=0.0.1",
    "ansys-mapdl-core>=0.68.0",
]

[project.scripts]
pymapdl-mcp = "pymapdl_mcp.__main__:main"
```

### Step 7: Run Your MCP Server

```bash
# Install your package
pip install -e .

# Run the MCP server
pymapdl-mcp
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
        return result["stdout"]
    return f"Error: {result['error']}"
```

### Using Command History

```python
from fastmcp.server.dependencies import get_context

@mcp.tool()
def get_command_history() -> list:
    """Get all executed commands."""
    ctx = get_context()
    app_context = ctx.fastmcp._lifespan_result
    return app_context.command_history

@mcp.tool()
def undo_last_command() -> str:
    """Undo the last command."""
    ctx = get_context()
    app_context = ctx.fastmcp._lifespan_result

    if not app_context.command_history:
        return "No commands to undo"
    last_cmd = app_context.command_history.pop()
    # Implement undo logic
    return f"Undone: {last_cmd}"
```

### Custom Startup Parameters

```python
class PyMAPDLMCP(PyAnsysBaseMCP):
    def __init__(self, mapdl_mode="grpc", *args, **kwargs):
        self.mapdl_mode = mapdl_mode
        super().__init__(*args, **kwargs)

    def product_startup(self):
        self.context.mapdl = launch_mapdl(mode=self.mapdl_mode)
```

### Restarting Python Session

The Python session can be manually restarted if it becomes unresponsive or if you want to reset the state. Command history is preserved in the context, allowing you to replay commands after restart.

```python
from fastmcp.server.dependencies import get_context

@mcp.tool()
def restart_python_session(replay_history: bool = True) -> str:
    """Restart the Python session and optionally replay command history.

    Parameters
    ----------
    replay_history : bool
        If True, replay all previous commands from history after restart

    Returns
    -------
    str
        Restart status message
    """
    ctx = get_context()
    app_context = ctx.fastmcp._lifespan_result

    # Restart the session (this clears variables/imports except startup_code)
    result = app_context.python_session.restart()

    if not result["success"]:
        return f"Failed to restart: {result.get('error')}"

    # Optionally replay command history to restore state
    if replay_history and app_context.command_history:
        from ansys.common.mcp.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info(f"Replaying {len(app_context.command_history)} commands...")

        for i, cmd in enumerate(app_context.command_history, 1):
            replay_result = app_context.python_session.execute(cmd)
            if not replay_result["success"]:
                return (
                    f"Session restarted but replay failed at command {i}/{len(app_context.command_history)}: "
                    f"{replay_result.get('error')}"
                )

        return f"Session restarted and {len(app_context.command_history)} commands replayed successfully"

    return "Session restarted successfully"
```

**Note:** The `command_history` is stored in the application context (not in the Python session), so it survives restarts. You can choose whether to replay the history to restore the session state.

## Best Practices

### 1. **Context Design**
- Keep only shared state in context
- Use typed fields (avoid `Any` when possible)
- Document what each field represents

### 2. **Tool Design**
- One tool = one clear action
- Descriptive names: `create_geometry` not `create`
- Comprehensive docstrings with parameter descriptions
- Handle errors gracefully, return meaningful messages

### 3. **Error Handling**
```python
def product_startup(self):
    try:
        self.context.mapdl = launch_mapdl()
    except Exception as e:
        print(f"Failed to launch MAPDL: {e}")
        raise  # Let the base class handle cleanup
```

### 4. **Logging**
```python
import logging
logger = logging.getLogger(__name__)

def product_startup(self):
    logger.info("Launching MAPDL...")
    self.context.mapdl = launch_mapdl()
    logger.info(f"MAPDL version: {self.context.mapdl.version}")
```

## Testing Your MCP Server

```python
# tests/test_server.py
import pytest
from pymapdl_mcp import PyMAPDLMCP

@pytest.fixture
def mcp_server():
    server = PyMAPDLMCP(name="test-server")
    return server

def test_context_creation(mcp_server):
    ctx = mcp_server.create_context()
    assert ctx is not None
    assert ctx.python_session is not None

def test_tool_execution(mcp_server):
    # Test your tools
    pass
```

## Troubleshooting

**Issue**: `TypeError: Can't instantiate abstract class`
- **Solution**: Ensure you've implemented `product_startup()`, `product_cleanup()`, and optionally `create_context()`

**Issue**: Tools can't access product instance
- **Solution**: Use `get_context()` from `fastmcp.server.dependencies` and access via `ctx.fastmcp._lifespan_result.mapdl`

**Issue**: `ctx parameter is required` error when calling tools
- **Solution**: Remove `ctx` from function parameters - it should be obtained via `get_context()` inside the function, not passed as a parameter

**Issue**: Python session fails to start
- **Solution**: Check `python_executable` path, verify permissions, check logs in stderr

**Issue**: Not seeing log messages
- **Solution**: Logs go to stderr by default. Set `LOGLEVEL=DEBUG` environment variable for more detail, or redirect stderr to a file: `python -m your_mcp 2> server.log`

**Issue**: Python session becomes unresponsive
- **Solution**: Use the `restart()` method on the Python session, optionally replaying command history from the context

## Examples

See complete example implementations:
- [PyMAPDL MCP](https://github.com/ansys/pymapdl-mcp) - MAPDL integration
- [PyFluent MCP](https://github.com/ansys/pyfluent-mcp) - Fluent integration

## Contributing

Contributions welcome! Please:
1. Follow existing code style
2. Add tests for new features
3. Update documentation

## License

MIT License - see LICENSE file for details.

## Support

- Issues: [GitHub Issues](https://github.com/ansys-internal/pyansys-common-mcp/issues)
- Email: pyansys.core@ansys.com
