Basics
======

``laminar`` has two main components, ``Flow`` and ``Layer``. A ``Flow`` is a collection of ``Layer`` which are combined together to define a workflow and perform tasks.

Registering Layers
------------------

A ``Layer`` must be registered with a ``Flow`` before it can be used in the ``Flow``:

.. code:: python

    from laminar import Flow, Layer

    flow = Flow("RegisterFLow")

    @flow.register()
    class A(Layer):
        ...

A ``Layer`` can be registered to multiple flows:

.. code:: python

    from laminar import Flow, Layer

    flow1 = Flow("Flow1")
    flow2 = Flow("Flow2")

    @flow1.register()
    @flow2.register()
    class A(Layer):
        ...

    @flow1.register()
    @flow2.register()
    class B(Layer):
        ...

Executing Flows
---------------

Once a ``Flow`` has all of its layers registered to it, it can be called in order to execute the workflow.

.. code:: python

    from laminar import Flow, Layer

    flow = Flow("TriggerFlow")

    @flow.register()
    class A(Layer):
        ...

    if __name__ == "__main__":
        flow()

Performing Tasks
----------------

A ``Layer`` is a unit of work, and can be customized to perform any action that can be defined in Python. To customize what a ``Layer`` does when executed, override ``Layer.__call__``.

.. code:: python

    # main.py

    from laminar import Flow, Layer

    flow = Flow("TaskFlow")

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            print("hello world")

    if __name__ == "__main__":
        flow()

.. code:: python

    python main.py

    >>> "hello world"

Dependencies
------------

Often tasks in a workflow need to be executed in a predefined order. Defining a ``Layer`` dependency is done by adding dependency layers with type annotations to ``__call__``. The type annotation is used to infer which layers depend on which other layers. In this two ``Layer`` example, ``B`` is dependent on ``A``:

.. code:: python

    # main.py

    from laminar import Flow, Layer

    flow = Flow("HelloFlow")

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            print(self.name)

    @flow.register()
    class B(Layer):
        def __call__(self, a: A) -> None:
            print(self.name)

    if __name__ == "__main__":
        flow()

.. code:: python

    python main.py

    >>> "A"
    >>> "B"

Dependencies can be arbitrarily complex but must represent a directed acyclic graph. Any ``Layer`` can have a dependency on any other ``Layer``, without cycles. Consider this extended example:

.. code:: python

    # main.py

    from laminar import Flow, Layer

    flow = Flow("HelloFlow")

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            print(self.name)

    @flow.register()
    class B(Layer):
        def __call__(self, a: A) -> None:
            print(self.name)

    @flow.register()
    class C(Layer):
        def __call__(self, b: B) -> None:
            print(self.name)

    @flow.register()
    class D(Layer):
        def __call__(self, a: A, c: C) -> None:
            print(self.name)

    if __name__ == "__main__":
        flow()

.. code:: python

    python main.py

    >>> "A"
    >>> "B"
    >>> "C"
    >>> "D"

Here ``A`` waits on ``A``, ``C`` waits on ``B``, and ``D`` waits on ``A`` and ``C`` to complete before running.

Artifacts
---------

Any value that is assigned to ``self`` is automatically saved and passed to the next ``Layer``. In this way, data is passed logically from one ``Layer`` to the next and are referenced directly using the ``dot`` attribute notation.

.. code:: python

    # main.py

    from laminar import Flow, Layer

    flow = Flow("HelloFlow")

    @flow.register()
    class Start(Layer):
        def __call__(self) -> None:
            self.message = "Hello World"
            print(f"Sending the message: {self.message}")

    @flow.register()
    class Middle(Layer):
        def __call__(self, start: Start) -> None:
            print(start.message)
            self.message = start.message

    @flow.register()
    class End(Layer):
        def __call__(self, middle: Middle) -> None:
            print(f"Sent message: {middle.message}")

    if __name__ == "__main__":
        flow()

.. code:: python

    python main.py

    >>> "Sending the message: Hello World"
    >>> "Hello World"
    >>> "Sent message: Hello World"
