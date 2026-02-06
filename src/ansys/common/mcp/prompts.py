"""Common prompts for PyAnsys MCP servers.

This module can be extended to include common prompts that are useful
across PyAnsys products. Product-specific prompts should be implemented
in the respective product MCP packages.
"""

# Prompt template for dynamic rule management
RULES_SYSTEM_PROMPT = """
# Automatic rule learning system

This MCP server automatically learns from errors to improve future interactions.
When code execution fails, the system generates a rule to prevent similar errors.

## How rules work:
1. When code fails, the error is analyzed by an LLM
2. A concise, actionable rule is generated
3. Rules are categorized for easy reference (e.g., "Division Operations", "PREP7 Commands")
4. Rules accumulate during the session to build a knowledge base

## Using rules:
- Check current rules using the `get_rules` tool before executing similar operations
- Rules are organized by category for easy navigation
- Rules are specific to the current session and context

## Rule format:
Rules are stored as:
```
Category name:
  - Rule description (actionable, imperative)
  - Another rule description
```

Example rules:
```
Division operations:
  - Do not divide by zero
  - Always check denominator before division

PREP7 commands:
  - Always enter PREP7 mode before defining geometry
  - Exit PREP7 before entering solution mode
```

Use rules to:
- Avoid repeating mistakes
- Understand context-specific constraints
- Learn best practices for the current workflow
"""

__all__ = ["RULES_SYSTEM_PROMPT"]
