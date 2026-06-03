# ansys.common.mcp
from importlib import import_module
from typing import List, Tuple

# List of tuples containing (tool_name, success, command)
commands_history: List[Tuple[str, bool, str]] = []


def get_tool_function(tool_name: str):
    """Get the function associated with a tool name.

    Parameters
    ----------
    tool_name : str
        Name of the tool to retrieve the function for, such as
        "ansys.mapdl.mcp.tools.run_python_code".

    Returns
    -------
    function : Callable
        The actual function object associated with the tool.

    Examples
    --------
    Retrieve a tool function:
    >>> run_python_code_func = get_tool_function("ansys.mapdl.mcp.tools.run_python_code")
    >>> run_python_code_func("print('Hello, World!')")
    """
    # Import the tool function
    module_name, function_name = tool_name.rsplit(".", 1)
    module = import_module(module_name)
    return getattr(module, function_name)


def rerun_history():
    """Rerun the command history."""
    for tool, success, command in commands_history:
        if success:
            print(f"Rerunning command from tool {tool}: {command}")
            tool_function = get_tool_function(tool)
            tool_function(command)


########################################################################
