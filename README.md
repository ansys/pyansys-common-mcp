# PyAnsys Common MCP

Common infrastructure for building Model Context Protocol (MCP) servers for PyAnsys libraries.

## What is this?

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

## Quick start: Create your product MCP server

### Step 1: Project structure

Create a new package for your product (e.g., `pyexample-mcp`):

```
pyexample-mcp/
├── pyproject.toml
├── README.md
└── src/
    └── pyexample_mcp/
        ├── __init__.py
        ├── __main__.py
        ├── server.py       # Your MCP server class
        ├── context.py      # Your custom context
        └── tools.py        # Your MCP tools
```

### Step 2: Define your custom context

Create `context.py` to add product-specific fields:

```python
# src/pyexample_mcp/context.py
from dataclasses import dataclass
from typing import Optional
from ansys.common.mcp import PyAnsysBaseAppContext

@dataclass
class PyExampleContext(PyAnsysBaseAppContext):
    """Product-specific context with product instance."""
    product: Optional[Any] = None  # Your product instance
    project_dir: Optional[str] = None  # Additional fields as needed
```

**Why?** The context holds your product instance and any state that needs to be shared across tools.

### Step 3: Create your MCP server

Create `server.py` implementing the two required methods:

- `product_startup()`: Initialize connections, launch products
- `product_cleanup()`: Close connections, clean up resources
- Python session management is handled automatically by the base class

### Step 4: Add your MCP tools

You can add tools in two ways: use the common tools or create product-specific tools.

#### Option A: Use common tools (recommended)

The common library provides ready-to-use tool implementations that you can directly wrap:

```python
# src/pyexample_mcp/tools.py
from fastmcp import Context
from ansys.example.mcp import app
from ansys.common.mcp.tools import execute_python_code, create_custom_plot, get_rules

@app.tool()
async def run_python_code(
    ctx: Context,
    code: str,
    timeout: int = 60,
    auto_generated_rules: bool = True,
) -> str:
    """
    Execute Python code with automatic rule learning.
    
    Parameters
    ----------
    ctx : Context
        The MCP context containing server session and application context.

    Returns
    -------
    str
        Command execution result.
    """
    return await execute_python_code(ctx, code, timeout, auto_generated_rules)

@app.tool()
def plot_custom_data(
    ctx: Context,
    plot_code: str,
    plot_type: str = "matplotlib",
    timeout: int = 60,
) -> list:
    """
    Create custom matplotlib or PyVista plots.
    
    Parameters
    ----------
    ctx : Context
        The MCP context containing server session and application context.
    plot_code : str
        Python code to create the plot. Should use matplotlib.pyplot or PyVista.
        For matplotlib, the code should create the figure/plot but NOT call plt.show().
        Use the save_matplotlib_plot() or save_plot() helper functions to return the plot.
    plot_type : str, optional
        Type of plot: "matplotlib" or "pyvista". Default is "matplotlib".
    timeout : int, optional
        Maximum time in seconds to allow for code execution. Default is 60 seconds.

    Returns
    -------
    str
        Command execution result.
    """
    return create_custom_plot(ctx, plot_code, plot_type, timeout)

@app.tool()
def get_session_rules(ctx: Context, category: str | None = None) -> str:
    """Get rules accumulated from errors during this session."""
    return get_rules(ctx, category)
```

#### Option B: Create product-specific tools

Add tools unique to your product:

```python
# src/pyexample_mcp/tools.py (continued)
@app.tool()
def run_specific_command(ctx: Context, command: str) -> str:
    """Execute a specific command.

    Parameters
    ----------
    ctx : Context
        The MCP context containing server session and application context.
    command : str
        Specific command to execute

    Returns
    -------
    str
        Command execution result.
    """
    app_context = ctx.request_context.lifespan_context
    
    if not app_context.product_session:
        return "Error: Product session is not connected"
    
    result = app_context.product_session.run(command)
    app_context.command_history.append(command)
    return result
```

#### Combining both approaches

**Tool guidelines:**
- Include `ctx: Context` as a parameter in your tool function signature
- Access app context via `ctx.request_context.lifespan_context`
- Use type hints for all parameters
- Write clear docstrings (AI assistants read these!)
- For common tools, simply wrap the imported function
- For product-specific tools, access your product instance from the context

### Step 5: Wire everything together

Create `__main__.py` to run your server:

```python
# src/pyexample_mcp/__main__.py
from pyexample_mcp.server import PyExampleMCP
from pyexample_mcp.tools import register_all_tools

# Create server instance
app = PyExampleMCP(name="PyExample MCP Server")

# Run the server
if __name__ == "__main__":
    app.run()
```

Create `__init__.py`:

```python
# src/pyexample_mcp/__init__.py
from pyexample_mcp.server import PyExampleMCP
from pyexample_mcp.context import PyExampleContext

__all__ = ["PyExampleMCP", "PyExampleContext"]
```

Create `__main__.py` for CLI execution:

```python
# src/pyexample_mcp/__main__.py
import sys
from pyexample_mcp import PyExampleMCP, register_tools

def main():
    # Initialize your MCP server
    mcp = PyExampleMCP(name="pyexample-mcp")

    # Register your tools
    register_tools(mcp)

    # Run the server
    mcp.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Step 6: Configure ``pyproject.toml``

```toml
[project]
name = "pyexample-mcp"
version = "0.1.0"
dependencies = [
    "ansys-common-mcp>=0.0.1",
]

[project.scripts]
pyexample-mcp = "pyexample_mcp.__main__:main"
```

### Step 7: Run your MCP server

```bash
# Install your package
pip install -e .

# Run the MCP server
pyexample-mcp
```

## Architecture overview

```
┌─────────────────────────────────────┐
│   Your Product MCP Server           │
│   (e.g., PyExampleMCP)              │
│                                     │
│   ├── create_context() ─────────────┼──> Returns YourContext
│   ├── product_startup() ────────────┼──> launch_product()
│   ├── product_cleanup() ────────────┼──> exit_product()
│   └── register_tools() ─────────────┼──> @app.tool() wrappers
└──────────────┬──────────────────────┘
               │ extends / uses
┌──────────────▼──────────────────────┐
│   PyAnsysBaseMCP (Base Class)       │
│   + Common Tools                    │
│                                     │
│   ├── product_lifespan() ───────────┼──> Manages lifecycle
│   ├── start_python_session() ───────┼──> Starts Python
│   ├── cleanup_python_session() ─────┼──> Stops Python
│   │                                 │
│   └── Common Tool Functions:        │
│       ├── execute_python_code() ────┼──> Execute code + rules
│       ├── create_custom_plot() ─────┼──> Plot generation
│       └── get_rules() ──────────────┼──> Access session rules
└─────────────────────────────────────┘
```

**What the base class handles:**
- ✅ Python session creation and management
- ✅ Lifecycle orchestration (startup → run → cleanup)
- ✅ Error handling and logging
- ✅ Context injection into tools
- ✅ Automatic rule learning from errors
- ✅ Reusable tool implementations

**What you implement:**
- ✅ Custom context with product-specific fields
- ✅ Product connection/initialization logic
- ✅ Tool registration (wrapping common tools + adding product-specific ones)
- ✅ Cleanup logic for your product

## Using common tools in your MCP server

The common library provides three ready-to-use tool implementations:

### 1. `execute_python_code` - Execute code with rule learning

```python
from ansys.common.mcp.tools import execute_python_code

@app.tool()
async def execute_python_code(
    code: str,
    ctx: Context,
    timeout: int = 60,
    auto_generated_rules: bool = True,
) -> str:
    """Execute Python code with automatic error rule generation."""
    return await execute_python_code(ctx, code, timeout, auto_generated_rules)
```

**Features:**
- Executes code in persistent Python session
- Automatically generates rules when code fails
- Returns JSON with stdout, stderr, and error details

### 2. `create_custom_plot` - Generate plots

```python
from ansys.common.mcp.tools import create_custom_plot

@app.tool()
def plot_data(
    plot_code: str,
    ctx: Context,
    plot_type: str = "matplotlib",
    timeout: int = 60,
) -> list:
    """Create matplotlib or PyVista plots."""
    return create_custom_plot(ctx, plot_code, plot_type, timeout)
```

**Features:**
- Supports matplotlib and PyVista
- Returns base64-encoded images
- Handles off-screen rendering automatically

### 3. `get_rules` - Access session rules

```python
from ansys.common.mcp.tools import get_rules

@app.tool()
def get_session_rules(ctx: Context, category: str | None = None) -> str:
    """Get rules learned during this session."""
    return get_rules(ctx, category)
```

**Features:**
- Returns all rules or rules for specific category
- Formatted output ready for LLM consumption
- Helps LLM avoid repeating errors

### Complete tool registration example

```python
# src/pyexample_mcp/tools.py
from fastmcp import Context
from ansys.common.mcp.tools import execute_python_code, create_custom_plot, get_rules

def register_all_tools(app):
    """Register all tools for PyExample MCP."""
    
    # Common tools
    @app.tool()
    async def execute_python_code(code: str, ctx: Context, timeout: int = 60) -> str:
        """Execute Python code with product access."""
        return await execute_python_code(ctx, code, timeout, auto_generated_rules=True)
    
    @app.tool()
    def plot_data(plot_code: str, ctx: Context, plot_type: str = "matplotlib") -> list:
        """Create custom plots."""
        return create_custom_plot(ctx, plot_code, plot_type)
    
    @app.tool()
    def get_session_rules(ctx: Context, category: str | None = None) -> str:
        """Get accumulated rules."""
        return get_rules(ctx, category)
    
    # Product-specific tools
    @app.tool()
    def run_product_command(command: str, ctx: Context) -> str:
        """Execute native product command."""
        app_context = ctx.request_context.lifespan_context
        if not app_context.product:
            return "Error: Product not connected"
        result = app_context.product.run(command)
        app_context.command_history.append(command)
        return result
```

## Logging

The framework automatically configures logging to output to **stderr** (not stdout, which is reserved for MCP protocol). This ensures log messages don't interfere with the MCP communication.

### Basic logging

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

### Configuring log level

You can control the log level via environment variable:

```bash
# Windows PowerShell
$env:LOGLEVEL="DEBUG"
python -m pyexample_mcp

# Linux/Mac
LOGLEVEL=DEBUG python -m pyexample_mcp
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

### Viewing logs

Logs are output to stderr, so you'll see them in your terminal when running the server. You can redirect them to a file:

```bash
# Windows PowerShell
python -m pyexample_mcp 2> server.log

# Linux/Mac
python -m pyexample_mcp 2> server.log
```

## Common Patterns

### Accessing Python session in tools

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

### Using command history

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

### Restarting Python session

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

## Best practices

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
        self.context.product = launch_product()
    except Exception as e:
        print(f"Failed to launch product: {e}")
        raise  # Let the base class handle cleanup
```

### 4. **Logging**
```python
import logging
logger = logging.getLogger(__name__)

def product_startup(self):
    logger.info("Launching product...")
    self.context.product = launch_product()
    logger.info(f"Product version: {self.context.product.version}")
```

## Testing your MCP server

```python
# tests/test_server.py
import pytest
from pyexample_mcp import PyExampleMCP

@pytest.fixture
def mcp_server():
    server = PyExampleMCP(name="test-server")
    return server

def test_context_creation(mcp_server):
    ctx = mcp_server.create_context()
    assert ctx is not None
    assert ctx.python_session is not None

def test_tool_execution(mcp_server):
    # Test your tools
    pass
```

## Automatic rule learning system

PyAnsys Common MCP includes an automatic rule learning system that helps the LLM improve over time by learning from errors.

### How it works

1. **Automatic Error Analysis**: When code execution fails, the system uses an LLM to analyze the error
2. **Rule Generation**: A concise, actionable rule is generated to prevent similar errors
3. **Categorization**: Rules are automatically categorized (e.g., "Division Operations", "PREP7 Commands", "Mesh Operations")
4. **Accumulation**: Rules build up during the session, creating a knowledge base specific to your workflow

### Using the rules system

#### In your tools

Use `execute_python_code` instead of directly executing code:

```python
from ansys.common.mcp import execute_python_code
from fastmcp import Context

@app.tool()
async def execute_code(code: str, ctx: Context) -> str:
    """Execute Python code with automatic rule generation."""
    return await execute_python_code(
        ctx=ctx,
        code=code,
        timeout=60,
        auto_generated_rules=True,
    )
```

#### Accessing rules

Create a tool to let the LLM check current rules:

```python
from ansys.common.mcp import get_rules

@app.tool()
def get_rules(category: str | None = None, ctx: Context = None) -> str:
    """Get current session rules to avoid repeating errors."""
    return get_rules(ctx, category=category)
```

#### Adding custom rules

You can manually add rules to the context in several ways:

**Method 1: Using context.add_rule() directly**
```python
app_context = ctx.request_context.lifespan_context
app_context.add_rule(
    category="PREP7 Commands",
    rule="Always enter PREP7 mode before defining geometry"
)
```

**Method 2: Using the update_rules helper (recommended)**
```python
from ansys.common.mcp import update_rules

app_context = ctx.request_context.lifespan_context

# Add a single rule
update_rules(
    app_context,
    category="Division Operations",
    rule="Do not divide by zero"
)

# Or add multiple rules at once
update_rules(
    app_context,
    rules_dict={
        "PREP7 Commands": [
            "Always enter PREP7 before defining geometry",
            "Exit PREP7 before entering solution mode"
        ],
        "Mesh Operations": [
            "Define element type before meshing"
        ]
    }
)
```

The `update_rules` helper automatically prevents duplicates and can be used in both single-rule and bulk modes.

### Rule examples

After running code that divides by zero:
```
Division operations:
  - Do not divide by zero
  - Always validate denominator before division
```

After product-specific errors:
```
Mesh operations:
  - Define element type before meshing
  - Set material properties before solving
```

### Using the rules prompt

Include the rules system prompt in your MCP server prompts:

```python
from ansys.common.mcp import RULES_SYSTEM_PROMPT

@app.prompt()
def system_instructions() -> str:
    """System instructions including rules guidance."""
    return f"""
    {RULES_SYSTEM_PROMPT}
    
    Additional product-specific instructions...
    """
```

### Benefits

- **Reduces repeated errors**: LLM learns from mistakes automatically
- **Organized knowledge**: Rules are categorized for easy reference
- **Context-specific**: Rules are tailored to your specific workflow
- **No manual intervention**: System learns automatically during normal usage

## Troubleshooting

**Issue**: `TypeError: Can't instantiate abstract class`
- **Solution**: Ensure you've implemented `product_startup()`, `product_cleanup()`, and optionally `create_context()`

**Issue**: Tools can't access product instance
- **Solution**: Use `get_context()` from `fastmcp.server.dependencies` and access via `ctx.fastmcp._lifespan_result.product`

**Issue**: `ctx parameter is required` error when calling tools
- **Solution**: Remove `ctx` from function parameters - it should be obtained via `get_context()` inside the function, not passed as a parameter

**Issue**: Python session fails to start
- **Solution**: Check `python_executable` path, verify permissions, check logs in stderr

**Issue**: Not seeing log messages
- **Solution**: Logs go to stderr by default. Set `LOGLEVEL=DEBUG` environment variable for more detail, or redirect stderr to a file: `python -m your_mcp 2> server.log`

**Issue**: Python session becomes unresponsive
- **Solution**: Use the `restart()` method on the Python session, optionally replaying command history from the context

**Issue**: Rules not being generated
- **Solution**: Ensure you're using `execute_python_code` with `auto_generated_rules=True`

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
