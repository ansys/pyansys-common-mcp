.. title:: PyAnsys Common MCP Documentation

.. meta::
   :keywords: pyansys, mcp, model context protocol, ai, claude, chatgpt
   :description: Common infrastructure for building MCP servers for PyAnsys libraries


PyAnsys Common MCP
==================

.. toctree::
   :hidden:
   :maxdepth: 3

   getting_started/index
   user_guide/index
   api/index
   examples/index

**PyAnsys Common MCP** is a foundational library for building Model Context Protocol (MCP)
servers that enable AI assistants (like Claude, ChatGPT) to interact with Ansys products
through PyAnsys libraries.

.. grid:: 1
   :gutter: 2
   :padding: 2

   .. grid-item-card:: 🎯 For PyAnsys Library Developers
      
      This library is designed for **PyAnsys library developers** who want to create
      MCP servers for their products. It provides the infrastructure to:
      
      - Manage persistent Python sessions for stateful AI interactions
      - Handle product lifecycle (startup, cleanup, error handling)
      - Create extensible, maintainable MCP servers
      - Follow consistent patterns across PyAnsys products

Key Features
------------

.. grid:: 2 2 2 2
   :gutter: 2

   .. grid-item-card:: 🐍 Persistent Python Sessions
      
      Maintain stateful Python environments across multiple AI requests,
      preserving variables, imports, and state between interactions.

   .. grid-item-card:: ♻️ Lifecycle Management
      
      Automatic startup, cleanup, and error handling for product connections
      with extensible hooks for custom initialization.

   .. grid-item-card:: 🏗️ Extensible Architecture
      
      Base classes and patterns specifically designed for PyAnsys products,
      making it easy to create consistent MCP servers.

   .. grid-item-card:: 📝 Logging Infrastructure
      
      Pre-configured logging to stderr that doesn't interfere with the MCP
      protocol, with environment-based configuration.

Quick Example
-------------

Creating an MCP server involves three steps:

.. code-block:: python

   # 1. Define custom context
   @dataclass
   class MyProductContext(PyAnsysBaseAppContext):
       product_instance: Optional[Any] = None

   # 2. Implement server
   class MyProductMCP(PyAnsysBaseMCP):
       def product_startup(self):
           self.context.product_instance = connect_to_product()
       
       def product_cleanup(self):
           self.context.product_instance.disconnect()

   # 3. Create tools
   @mcp.tool()
   def execute_command(command: str) -> str:
       ctx = get_context()
       return ctx.fastmcp._lifespan_result.product_instance.run(command)

What do you want to do?
------------------------

.. grid:: 2 2 3 3
    :gutter: 2
    :padding: 2

    .. grid-item-card:: :fa:`rocket` Get Started
        :link: ref_getting_started
        :link-type: ref

        Learn how to install PyAnsys Common MCP and create your first
        MCP server in minutes.

    .. grid-item-card:: :fa:`book-open` User Guide
        :link: ref_user_guide
        :link-type: ref

        Deep dive into architecture, advanced patterns, and best practices
        for building robust MCP servers.

    .. grid-item-card:: :fa:`code` Examples
        :link: ref_examples
        :link-type: ref

        Complete working examples including PyExample-MCP and links to
        production implementations like PyMAPDL-MCP.

    .. grid-item-card:: :fa:`file-code` API Reference
        :link: api_ref
        :link-type: ref

        Detailed API documentation for all classes, methods, and functions
        in PyAnsys Common MCP.

Real-World Implementations
--------------------------

See these production MCP servers built with PyAnsys Common MCP:

- `PyMAPDL-MCP <https://github.com/ansys/pymapdl-mcp>`_ - MCP server for PyMAPDL

Architecture Overview
---------------------

.. code-block:: text

   ┌─────────────────────────────────────┐
   │  AI Client (Claude, ChatGPT)        │
   └────────────┬────────────────────────┘
                │ MCP Protocol
   ┌────────────▼────────────────────────┐
   │  Your Product MCP Server            │
   │  • Custom context & tools           │
   │  • Product startup/cleanup          │
   └────────────┬────────────────────────┘
                │ extends
   ┌────────────▼────────────────────────┐
   │  PyAnsysBaseMCP                     │ 
   │  ✅ Lifecycle management           │
   │  ✅ Python session handling        │
   │  ✅ Error handling & logging       │
   └─────────────────────────────────────┘

The base class handles infrastructure while you focus on product-specific logic.

Installation
------------

.. code-block:: bash

   pip install ansys-common-mcp

For development:

.. code-block:: bash

   pip install ansys-common-mcp[dev]

Support and Resources
---------------------

- **Documentation**: https://github.com/ansys/pyansys-common-mcp
- **Issues**: https://github.com/ansys/pyansys-common-mcp/issues
- **Discussions**: https://github.com/ansys/pyansys-common-mcp/discussions
- **Email**: pyansys.core@ansys.com
- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/jlowin/fastmcp

