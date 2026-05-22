
# ansys.common.mcp

TOOL_REGISTRY = {
    "ansys.common.mcp.tools.run_python_code",
}

def discover_tools(path_to_module: str) -> None:
    """Discover tools in a given module."""
    # This is a placeholder implementation. In a real implementation, you would
    # use something like importlib to dynamically import the module and inspect
    # its contents to find tools.
    from importlib import import_module
    
    module = import_module(path_to_module)
    
    #Discover tools in the module and add them to the registry
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if callable(attr) and hasattr(attr, "_is_tool"): # to be checked if this if really works... we need to check for the mcp.tool decorator
            tool_name = f"tool_{path_to_module.split('.')[-1]}_{attr_name}"
            TOOL_REGISTRY.add(f"{path_to_module}.{attr_name}")

#----------------------------------------------------------------------------------
# ansys.mapdl.mcp

class MapdlMcp:
    def __init__(self):
        # ...
        
        from ansys.common.mcp import discover_tools
        
        discover_tools("ansys.mapdl.mcp.tools")



