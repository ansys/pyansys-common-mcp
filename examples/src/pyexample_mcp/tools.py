"""Tools for PyExample MCP server."""

import json
from typing import Optional

from fastmcp.server import Context
from pyexample_mcp import app

from ansys.common.mcp.logging_config import get_logger

logger = get_logger(__name__)


# Define tools for interacting with PyExample instance
@app.tool()
def execute_command(ctx: Context, command: str) -> str:
    """Execute a PyExample command.

    Parameters
    ----------
    command : str
        PyExample command to execute

    Returns
    -------
    str
        Command execution result
    """
    app_context = ctx.fastmcp._lifespan_result

    if not app_context.example_instance:
        return "Error: PyExample not connected"

    try:
        result = app_context.example_instance.run_command(command)
        app_context.command_history.append(command)
        logger.info(f"Executed command: {command}")
        return str(result)
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return f"Error: {e}"


@app.tool()
def create_model(
    ctx: Context,
    name: str,
    model_type: str = "default",
    parameters: Optional[dict] = None,
) -> str:
    """Create a new model in PyExample.

    Parameters
    ----------
    name : str
        Name for the new model
    model_type : str
        Type of model to create
    parameters : Optional[dict]
        Additional model parameters

    Returns
    -------
    str
        Status message
    """
    app_context = ctx.fastmcp._lifespan_result

    if not app_context.example_instance:
        return "Error: PyExample not connected"

    # Create model (simulated)
    params = parameters or {}
    model = app_context.example_instance.create_model(name, model_type, **params)

    # Update command history
    command = f"CREATE MODEL {name} TYPE {model_type}"
    app_context.command_history.append(command)

    logger.info(f"Created model: {name} (type: {model_type})")
    return f"Model '{name}' created successfully\n{model}"


@app.tool()
def run_simulation(
    ctx: Context, model_name: Optional[str] = None, save_results: bool = True
) -> str:
    """Run a simulation on the specified model.

    Parameters
    ----------
    model_name : Optional[str]
        Model to simulate (uses active model if not specified)
    save_results : bool
        Whether to save results in context

    Returns
    -------
    str
        Simulation results summary
    """
    app_context = ctx.fastmcp._lifespan_result

    if not app_context.example_instance:
        return "Error: PyExample not connected"

    # Determine which model to use
    target_model = model_name or app_context.example_instance.active_model

    if not target_model:
        return "Error: No model specified or active"

    # Run simulation (simulated)
    command = f"SOLVE MODEL {target_model}"
    result = app_context.example_instance.run_command(command)

    # Save results if requested
    if save_results:
        app_context.simulation_results[target_model] = {"status": "completed", "summary": result}

    app_context.command_history.append(command)
    logger.info(f"Simulation completed for model: {target_model}")

    return f"Simulation completed for '{target_model}'\n{result}"


@app.tool()
def get_command_history(ctx: Context, format: str = "list") -> str:
    """Retrieve command execution history.

    Parameters
    ----------
    format : str
        Output format: 'list', 'numbered', or 'json'

    Returns
    -------
    str
        Command history in requested format
    """
    app_context = ctx.fastmcp._lifespan_result

    if not app_context.command_history:
        return "No commands executed yet"

    if format == "numbered":
        lines = [f"{i+1}. {cmd}" for i, cmd in enumerate(app_context.command_history)]
        return "\n".join(lines)

    elif format == "json":
        return json.dumps(app_context.command_history, indent=2)

    else:  # list format
        return "\n".join(app_context.command_history)


@app.tool()
def execute_python_code(ctx: Context, code: str) -> str:
    """Execute Python code in the persistent session.

    This allows for custom analysis and processing using the
    full Python ecosystem.

    Parameters
    ----------
    code : str
        Python code to execute

    Returns
    -------
    str
        Execution output
    """
    app_context = ctx.fastmcp._lifespan_result

    result = app_context.python_session.execute(code)

    if result["success"]:
        output = str(result["stdout"])
        if result["stderr"]:
            output += f"\n\nWarnings:\n{result['stderr']}"
        return output
    else:
        return f"Error: {result['error']}"
