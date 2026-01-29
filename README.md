# PyAnsys Common MCP

[![PyAnsys](https://img.shields.io/badge/Py-Ansys-ffc107.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABDklEQVQ4jWNgoDfg5+OQgMJ/0AqCqXGQMEBAwBEKQj5gGDjQsA80UeCDscxrD4YhGsgABEELnC5zAwAu6ADCKQDAQzNBFwAAVdgFEAnfDiQAATyIBaAFgCbkAI5DQwAVGAYkAMA4gHgg2AC+AAgQIABggagAqyAD4AF0MaB8gCbgoEAL0MEYRz4WxpMdWFzQBYKhK8DjEYH9KDgAw9ACAAgwFCgC2AMJvgAAJv+LQQJwJ8AAKQEoAAxr7W4AG/wGqAB4AACkR7cEdcEBQOPjIvAEtRDoAbYLANQAZGsBEAFeBwCsAY0HgGCAAEQTaDj7xQAABItJ+S3DsQAAAABJRU5ErkJggg==)](https://docs.pyansys.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Common infrastructure for building [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers for PyAnsys libraries.

## Overview

This package provides the foundation for creating MCP servers that enable AI assistants (like Claude, ChatGPT) to interact with Ansys products through PyAnsys libraries.

**Key Features:**
- **Persistent Python sessions** - Stateful code execution across multiple AI requests
- **Lifecycle management** - Automatic startup, cleanup, and error handling
- **Extensible architecture** - Base classes and patterns for product-specific implementations
- **Logging infrastructure** - Pre-configured logging that doesn't interfere with MCP protocol

## Installation

As the library is published to the private PyPI, the ``PYANSYS_PYPI_PRIVATE_PAT`` key is needed for the installation process.

```bash
pip install ansys-common-mcp --extra-index-url https://${{ secrets.PYANSYS_PYPI_PRIVATE_PAT }}@pkgs.dev.azure.com/pyansys/_packaging/pyansys/pypi/simple/
```


For developers contributing to PyAnsys Common MCP or creating custom servers:
```bash
# Clone the repository
git clone https://github.com/ansys/pyansys-common-mcp.git
cd pyansys-common-mcp

# Install in editable mode with dev dependencies
pip install -e .[dev]

# Or for documentation building
pip install -e .[doc]
```

## Quick Start

Creating an MCP server for your PyAnsys library involves three main steps:

1. **Define your custom context** - Extend `PyAnsysBaseAppContext` to store product-specific state
2. **Implement your MCP server** - Extend `PyAnsysBaseMCP` with startup/cleanup logic
3. **Create MCP tools** - Define tools that interact with your product

## Real-World Example

See **[PyMAPDL-MCP](https://github.com/ansys/pymapdl-mcp)** for a complete, production-ready implementation.

## Documentation

Full documentation available at:
- **Documentation**: [Full documentation](https://refactored-chainsaw-r6q6r7j.pages.github.io/)
- **Issues**: [GitHub issues](https://github.com/ansys/pyansys-common-mcp/issues)
- **Email**: pyansys.core@ansys.com
- **Discussions**: [GitHub discussions](https://github.com/ansys/pyansys-common-mcp/discussions)
