





:class:`PyAnsysBaseAppContext`
==============================


.. py:class:: src.ansys.common.mcp.context.PyAnsysBaseAppContext

   
   Base application context for PyAnsys MCP servers.

   This provides a common structure that product-specific contexts
   can extend. The product_instance field can hold any Ansys product
   connection (MAPDL, Fluent, Maxwell, etc.).


   :Attributes:

       **product_instance** : :obj:`Optional`\[:obj:`Any`]
           The main product instance (e.g., MAPDL, Fluent) associated with the context.

       **python_executable** : :obj:`Optional`\[:obj:`Any`]
           The Python executable used for the session.

       **python_session** : :obj:`Optional`\[:obj:`Any`]
           An instance of PersistentPythonSession for managing a persistent
           Python session.

       **metadata** : :class:`python:dict`
           A dictionary for storing arbitrary metadata related to the context.

       **command_history** : :class:`python:list`
           A list to keep track of executed commands in the session.












   .. rubric:: Examples

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

   ..
       !! processed by numpydoc !!


.. py:currentmodule:: PyAnsysBaseAppContext

Overview
--------

.. tab-set::





   .. tab-item:: Attributes

      .. list-table::
          :header-rows: 0
          :widths: auto

          * - :py:attr:`~product_instance`
            - 
          * - :py:attr:`~python_executable`
            - 
          * - :py:attr:`~python_session`
            - 
          * - :py:attr:`~metadata`
            - 
          * - :py:attr:`~command_history`
            - 






Import detail
-------------

.. code-block:: python

    from src.ansys.common.mcp.context import PyAnsysBaseAppContext


Attribute detail
----------------

.. py:attribute:: product_instance
   :type:  Optional[Any]
   :value: None


.. py:attribute:: python_executable
   :type:  Optional[Any]
   :value: None


.. py:attribute:: python_session
   :type:  Optional[Any]
   :value: None


.. py:attribute:: metadata
   :type:  dict

.. py:attribute:: command_history
   :type:  list
   :value: []






