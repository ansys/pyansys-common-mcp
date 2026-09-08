.. _ref_user_guide:

==========
User guide
==========

This guide provides comprehensive documentation for building MCP servers using
PyAnsys Common MCP. It covers both architectural concepts and practical patterns.

Overview
========

PyAnsys Common MCP provides infrastructure for creating Model Context Protocol (MCP)
servers that enable AI assistants to interact with Ansys products through PyAnsys libraries.

The library handles:

- **Lifecycle management** - Automatic startup, cleanup, and error handling
- **Python sessions** - Persistent Python environments for stateful code execution
- **Context management** - Shared state accessible from all tools
- **Logging** - Pre-configured logging that doesn't interfere with MCP protocol

Your job as a library developer is to:

- **Define custom context** - Extend ``PyAnsysBaseAppContext`` with product-specific fields
- **Implement server** - Extend ``PyAnsysBaseMCP`` with startup/cleanup logic
- **Create tools** - Define MCP tools that expose product functionality

What's next?
============

- :ref:`user_guide_architecture` - Deep dive into how the framework works
- :ref:`user_guide_advanced_patterns` - Advanced techniques and patterns
- :ref:`ref_examples` - Complete working examples

.. toctree::
   :maxdepth: 2
   :hidden:

   architecture
   advanced_patterns
