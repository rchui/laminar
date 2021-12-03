Laminar
=======

*slow is smooth, and smooth is fast*

``laminar`` is a modern container first framework for creating production ready workflows.

Easy to Write
-------------

``laminar`` brings together many of the best ideas from the various workflow frameworks that came before it. The
specifications are declarative, and concepts are consistent throughout the framework.

Container First
---------------

Containers are first class citizens in ``laminar`` flows. Containers are both used as a "write once, deploy anywhere"
method of packaging software applications for portability, and for comparmentalization and isolation of ``laminar`` flow
layers from each other.

Total Control
-------------

``laminar`` flows are highly configurable, both statically at definition time, and dynamically at run time.

Any Scale
---------

``laminar`` can scale to any size of compute. From small locally run prototypes to tens of thousands of concurrent
executions running in the cloud, ``laminar`` can handle it all.


.. toctree::
    :maxdepth: 4
    :caption: Getting Started
    :hidden:

    Introduction <self>
    Installation <getting_started/installation>
    Basics <getting_started/basics>

.. toctree::
    :maxdepth: 4
    :caption: Layers
    :hidden:

    Scaling Up <layers/scaling_up>
    Scaling Out <layers/scaling_out>
    Configuration <layers/configuration>

.. toctree::
    :maxdepth: 4
    :caption: Flows
    :hidden:

    Datastores <flows/datastores>
    Executors <flows/executors>
    Results <flows/results>

.. toctree::
    :maxdepth: 4
    :caption: Testing
    :hidden:

    Flows <testing/flows>
    Layers <testing/layers>
    Hooks <testing/hooks>

.. toctree::
    :maxdepth: 4
    :caption: Advanced
    :hidden:

    Datastores <advanced/datastores>
    Hooks <advanced/hooks>
