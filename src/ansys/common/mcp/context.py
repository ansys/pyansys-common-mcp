"""Common context definitions for PyAnsys MCP servers.

This module provides base context classes that can be extended by
product-specific MCP implementations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["PyAnsysBaseAppContext"]


@dataclass
class PyAnsysBaseAppContext:
    """Base application context for PyAnsys MCP servers.

    This provides a common structure that product-specific contexts
    can extend. The product_instance field can hold any Ansys product
    connection (MAPDL, Fluent, Maxwell, etc.).

    Attributes
    ----------
    product_instance : Optional[Any]
        The main product instance (e.g., MAPDL, Fluent) associated with the context.
    python_executable : Optional[Any]
        The Python executable used for the session.
    python_session : Optional[Any]
        An instance of PersistentPythonSession for managing a persistent
        Python session.
    metadata : dict
        A dictionary for storing arbitrary metadata related to the context.
    command_history : list
        A list to keep track of executed commands in the session.
    rules: dict
        A dictionary to store any rules or configurations relevant to the context.

    Examples
    --------
    Extend the base context for a specific product:

    >>> from ansys.common.mcp import PyAnsysBaseAppContext
    >>> from dataclasses import dataclass
    >>> from typing import Optional, Any
    >>>
    >>> @dataclass
    >>> class MAPDLAppContext(PyAnsysBaseAppContext):
    ...     mapdl: Optional[Any] = None
    ...
    ...     @property
    ...     def product_instance(self):
    ...         return self.mapdl
    """

    product_instance: Optional[Any] = None
    python_executable: Optional[Any] = None
    python_session: Optional[Any] = None  # PersistentPythonSession instance
    metadata: dict = field(default_factory=dict)
    command_history: list = field(default_factory=list)
    rules: dict = field(default_factory=dict)

    def add_rule(self, category: str, rule: str) -> None:
        """Add a rule to the context under a specific category.

        Parameters
        ----------
        category : str
            The category for the rule (e.g., "PREP7", "Division", "General").
        rule : str
            The rule description.
        """
        if category not in self.rules:
            self.rules[category] = []
        if rule not in self.rules[category]:
            self.rules[category].append(rule)

    def get_rules(self, category: Optional[str] = None) -> dict | list:
        """Get rules from the context.

        Parameters
        ----------
        category : Optional[str]
            If specified, return only rules for that category.
            If None, return all rules.

        Returns
        -------
        dict | list
            All rules as a dict if category is None, or a list of rules for the category.
        """
        if category is None:
            return self.rules
        return self.rules.get(category, [])

    def get_rules_formatted(self) -> str:
        """Get all rules formatted as a readable string.

        Returns
        -------
        str
            Formatted string of all rules organized by category.
        """
        if not self.rules:
            return "No rules defined yet."

        formatted = "Current Rules:\n"
        for category, rule_list in sorted(self.rules.items()):
            formatted += f"\n{category}:\n"
            for rule in rule_list:
                formatted += f"  - {rule}\n"
        return formatted
