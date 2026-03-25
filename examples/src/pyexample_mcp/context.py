"""Context for PyExample MCP server."""

from dataclasses import dataclass, field
from typing import Any, Optional

from ansys.common.mcp import PyAnsysBaseAppContext


@dataclass
class PyExampleContext(PyAnsysBaseAppContext):
    """Application context for PyExample MCP server.

    Attributes
    ----------
    example_instance : Optional[Any]
        The connected PyExample instance
    simulation_results : dict
        Storage for simulation results

    """

    example_instance: Optional[Any] = None
    simulation_results: dict = field(default_factory=dict)
