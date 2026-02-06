"""Common tool implementations for PyAnsys MCP servers.

This module provides reusable tool functions that product-specific MCP
servers can use or extend. These are not registered tools themselves,
but functions that can be called from product-specific tool implementations.
"""

import asyncio
import json

from fastmcp import Context
from mcp.types import ImageContent, TextContent

from ansys.common.mcp.helpers import _sanitize_output, generate_rule_from_error, logger


async def run_python_code(
    ctx: Context,
    code: str,
    timeout: int = 60,
    auto_generate_rules: bool = True,
) -> str:
    """Execute arbitrary Python code in the persistent Python session with automatic rule generation.

    This function should be used for custom Python code execution. When code execution
    fails, it automatically generates a rule using LLM analysis to prevent similar
    errors in the future.

    Parameters
    ----------
    ctx : Context
        The MCP context containing server session and application context.
    code : str
        The Python code to execute.
    timeout : int, optional
        Maximum time in seconds to allow for code execution. Default is 60 seconds.
    auto_generate_rules : bool, optional
        Whether to automatically generate rules from errors. Default is True.

    Returns
    -------
    str
        Execution result or error message. Returns JSON for structured output
        compatible with both stdio and http transports.

    Examples
    --------
    Execute simple Python code:
    >>> code = '''
    ... result = sum([i**2 for i in range(10)])
    ... print(f"Sum of squares: {result}")
    ... '''
    >>> await run_python_code(ctx, code)

    Execute code with automatic rule generation on failure:
    >>> code = "result = 1/0"  # This will fail
    >>> await run_python_code(ctx, code)
    # Automatically adds rule like: {"Division Operations": ["Do not divide by zero"]}
    """
    app_context = ctx.request_context.lifespan_context
    session = app_context.python_session

    if session is None:
        return json.dumps(
            {
                "success": False,
                "error": "No Python session available. The persistent Python session was not initialized.",
            },
            ensure_ascii=False,
        )

    try:
        # Sanitize the input code to remove problematic Unicode characters
        sanitized_code = _sanitize_output(code)

        logger.info(f"Executing Python code in persistent session:\n{sanitized_code}")

        # Execute code in persistent session
        result = session.execute(sanitized_code, timeout=timeout)

        # Parse the result
        if isinstance(result, dict):
            stdout = _sanitize_output(result.get("stdout", ""))
            stderr = _sanitize_output(result.get("stderr", ""))

            if result.get("success"):
                return json.dumps(
                    {
                        "success": True,
                        "stdout": stdout,
                        "stderr": stderr,
                        "message": "Python code executed successfully",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                # Execution failed - generate rule if enabled
                error_msg = result.get("error", "Unknown error occurred")
                error_msg = _sanitize_output(error_msg)

                if auto_generate_rules:
                    try:
                        logger.info("Generating rule from error...")
                        rule_info = await generate_rule_from_error(
                            code=sanitized_code,
                            error=error_msg,
                        )

                        # Add rule to context
                        if hasattr(app_context, "add_rule"):
                            app_context.add_rule(
                                category=rule_info["category"],
                                rule=rule_info["rule"],
                            )
                            logger.info(
                                f"Added rule - Category: {rule_info['category']}, Rule: {rule_info['rule']}"
                            )
                    except Exception as e:
                        logger.error(f"Failed to generate rule: {e}")

                return json.dumps(
                    {
                        "success": False,
                        "stdout": stdout,
                        "stderr": stderr,
                        "error": error_msg,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
        else:
            # Fallback if result is not a dict
            return json.dumps(
                {
                    "success": True,
                    "stdout": _sanitize_output(str(result)) if result else "",
                    "stderr": "",
                    "message": "Python code executed successfully",
                },
                ensure_ascii=False,
                indent=2,
            )

    except TimeoutError:
        error_dict = {
            "success": False,
            "error": f"Python code execution timed out after {timeout} seconds",
        }
        logger.error(error_dict["error"])
        return json.dumps(error_dict, ensure_ascii=False)

    except Exception as e:
        error_dict = {"success": False, "error": f"Error executing Python code: {str(e)}"}
        logger.error(error_dict["error"])
        return json.dumps(error_dict, ensure_ascii=False)


def create_custom_plot(
    ctx: Context,
    plot_code: str,
    plot_type: str = "matplotlib",
    timeout: int = 60,
) -> list[TextContent | ImageContent] | str:
    """Create a custom plot using matplotlib or PyVista in the persistent Python session.

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
        Maximum time in seconds for plot generation. Default is 60 seconds.

    Returns
    -------
    list[TextContent | ImageContent]
        A list containing:
        - TextContent with the plot creation status message
        - ImageContent with the base64-encoded image data if successfull
        or a JSON string with error details if failed.

    Examples
    --------
    Create a custom matplotlib line plot:
    >>> plot_code = '''
    ... import matplotlib.pyplot as plt
    ... import numpy as np
    ...
    ... # Extract data from MAPDL
    ... displacements = mapdl.get_array("NODE", item1="U", it1num="Y")
    ...
    ... # Create custom plot
    ... plt.figure(figsize=(10, 6))
    ... plt.plot(displacements)
    ... plt.xlabel("Node Number")
    ... plt.ylabel("Displacement (m)")
    ... plt.title("Custom Displacement Plot")
    ... plt.grid(True)
    ...
    ... # Save and return
    ... result = save_matplotlib_plot(dpi=150)
    ... print(result)
    ... '''
    >>> create_custom_plot(ctx, plot_code, plot_type="matplotlib")
    """
    session = ctx.request_context.lifespan_context.python_session

    if session is None:
        return [
            TextContent(
                type="text",
                text="No Python session available. The persistent Python session was not initialized.",  # noqa: E501
            )
        ]

    try:
        logger.info(f"Creating custom {plot_type} plot in persistent session")

        # Sanitize the plot code to remove problematic Unicode characters
        # This prevents encoding issues on Windows systems with limited charsets
        sanitized_plot_code = _sanitize_output(plot_code)

        # Execute the plot code
        result = session.execute(sanitized_plot_code, timeout=timeout)

        # Parse the result
        if isinstance(result, dict):
            stdout = _sanitize_output(result.get("stdout", ""))
            stderr = _sanitize_output(result.get("stderr", ""))

            if result.get("success"):
                # Try to extract plot data from stdout
                # The helper functions return data URI format:
                # "data:image/png;base64,<base64_string>"
                plot_data = stdout.strip()

                # Check if the output contains a base64 data URI
                if "data:image/png;base64," in plot_data:
                    # Extract the base64 part
                    base64_data = plot_data.split("data:image/png;base64,")[1].strip()

                    return [
                        TextContent(
                            type="text",
                            text=f"Custom {plot_type} plot created successfully",
                        ),
                        ImageContent(type="image", data=base64_data, mimeType="image/png"),
                    ]
                elif plot_data.startswith("Plot saved to"):
                    # File path returned
                    return [
                        TextContent(
                            type="text",
                            text=f"Custom {plot_type} plot created successfully\n{plot_data}",
                        )
                    ]
                else:
                    # Unexpected output format
                    return [
                        TextContent(
                            type="text",
                            text=f"Plot created but unexpected output format:\n{stdout}",
                        )
                    ]
            else:
                error_msg = result.get("error", "Unknown error occurred")
                error_msg = _sanitize_output(error_msg)
                return [
                    TextContent(
                        type="text",
                        text=f"Error creating custom {plot_type} plot: {error_msg}\nStdout: {stdout}\nStderr: {stderr}",  # noqa: E501
                    )
                ]
        else:
            # Fallback if result is not a dict
            return [
                TextContent(
                    type="text",
                    text=f"Unexpected result format: {_sanitize_output(str(result)) if result else 'No result'}",  # noqa: E501
                )
            ]

    except TimeoutError:
        error_msg = f"Plot creation timed out after {timeout} seconds"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

    except Exception as e:
        error_msg = f"Error creating custom plot: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]


def get_rules(ctx: Context, category: str | None = None) -> str:
    """Get the current rules from the context.

    This function retrieves rules that have been accumulated during the session
    to help the LLM avoid repeating similar errors.

    Parameters
    ----------
    ctx : Context
        The MCP context containing server session and application context.
    category : str | None, optional
        If specified, return only rules for that category.
        If None, return all rules organized by category.

    Returns
    -------
    str
        Formatted string of rules, or JSON if no rules exist.

    Examples
    --------
    Get all rules:
    >>> get_rules(ctx)

    Get rules for a specific category:
    >>> get_rules(ctx, category="PREP7")
    """
    app_context = ctx.request_context.lifespan_context

    if not hasattr(app_context, "get_rules_formatted"):
        return json.dumps(
            {
                "success": False,
                "error": "Context does not support rules. Update to latest PyAnsysBaseAppContext.",
            },
            ensure_ascii=False,
        )

    try:
        if category is not None:
            # Get rules for specific category
            rules = app_context.get_rules(category=category)
            if not rules:
                return f"No rules found for category: {category}"

            formatted = f"Rules for {category}:\n"
            for rule in rules:
                formatted += f"  - {rule}\n"
            return formatted
        else:
            # Get all rules formatted
            return app_context.get_rules_formatted()

    except Exception as e:
        error_msg = f"Error getting rules: {str(e)}"
        logger.error(error_msg)
        return json.dumps(
            {"success": False, "error": error_msg},
            ensure_ascii=False,
        )


__all__ = [
    "run_python_code",
    "create_custom_plot",
    "get_rules",
]
