Scaling Up
==========

Container
---------

Not all layers in a ``Flow`` need to use the same resources. Some layers might be memory focused and require many gigabytes of memory, and others might be compute focused and require many CPUs. ``laminar`` provides a layer ``Container`` configuration that can modify the settings of the container the ``Layer`` is being run in.

.. code:: python

    from laminar import Flow, Layer
    from laminar.configurations.layers import Container

    flow = Flow("ConfiguredFlow")

    @flow.register(container=Container(cpu=4, memory=2000, workdir="/app"))
    class Task(Layer):
        ...

A ``Container`` configuration can be shared across multiple layers.

.. code:: python

    from laminar import Flow, Layer
    from laminar.configurations.layers import Container

    flow = Flow("ConfiguredFlow")

    container = Container(cpu=4, memory=2000, workdir="/app")

    @flow.register(container=container)
    class First(Layer):
        ...

    @flow.register(container=container)
    class Second(Layer):
        ...
