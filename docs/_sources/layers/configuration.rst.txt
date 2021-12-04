Layer Configuration
===================

Access
------

Configurations are a part of the class definition of a ``Layer`` and are available as an atttribute of the ``Layer``. All ``Layer`` configurations are nested underneath the ``Layer.configuration`` attribute.

.. code:: python

    # main.py

    from laminar import Flow, Layer
    from laminar.configurations.layers import Container

    flow = Flow("ConfiguredFlow")

    @flow.register(container=Container(cpu=4, memory=2000, workdir="/app"))
    class Task(Layer):
        def __call__(self) -> None:
            print(self.configuration.container.cpu, self.configuration.container.memory)

    if __name__ == '__main__':
        flow()

.. code:: python

    python main.py

    >>> 4 2000

.. warning::

    If a hook changes a value in ``Layer.configuration``, that change will not be reflected in ``Layer.__call__``.

Retry
-----

Maybe requests to other services can be flaky or maybe you want your ``Flow`` to be tolerant of AWS EC2 Spot failures. Whatever the reason, there are situations where it is useful for layers to be retried on failure.

``Retry`` allows the user to configure the retry policy per layer.

.. code::

    from laminar import Flow, Layer
    from laminar.configurations import layers

    flow = Flow("RetryFlow")

    @flow.register(retry=layers.Retry(attempts=3))
    class A(Layer):
        ...
