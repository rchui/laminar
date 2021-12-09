Executors
=========

A ``Flow`` supports multiple backend executors which configure how work is executed in the workflow.

Docker
------

By default, flows are configured to use the ``Docker`` executor which launches each ``Layer`` registered to a ``Flow`` in its own docker container. The launched containers can be configured with the layer's ``Container`` configuration.

.. code:: python

    from laminar import Flow
    from laminar.configurations import executors, layers

    flow = Flow("DockerFlow", executor=executors.Docker())

    @flow.register(container=layers.Container(cpu=1, memory=1500))
    class A(Layer):
        ...

Thread
------

The ``Thread`` executor executes layers directly in the main Python process. This is very useful for testing.

.. code:: python

    from laminar import Flow
    from laminar.configurations import executors

    flow = Flow("ThreadFlow", executor=executors.Thread())

AWS.Batch
---------

.. warning::

    ``AWS.Batch`` is experimental.

The ``AWS.Batch``` executor executes layers in AWS Batch compute service.

.. code:: python

    from laminar import Flow
    from laminar.configurations import executors

    flow = Flow("BatchFlow", executor=executors.AWS.Batch())
