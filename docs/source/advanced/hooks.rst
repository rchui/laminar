Hooks
=====

``laminar`` supports a hook system for users to extend the existing functionality and dynamically adjust the flow in response to changes that occur at execution time. Hooks are Python generators that can perform actions before and after events occur within the flow.

An example of an execution hook in action:

.. code:: python

    # main.py

    from typing import Generator

    from laminar import Flow, Layer
    from laminar.configurations import hooks

    flow = Flow("Flow")

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            print("in call")

        @hooks.execution
        def hello_world(self) -> Generator[None, None, None]:
            print("before call")
            yield
            print("after call")

    if __name__ == "__main__":
        flow()

.. code:: python

    python main.py

    >>> "before call"
    >>> "in call"
    >>> "after call"

Execution Hooks
---------------

Execution hooks run just prior to the invocation of ``Layer.__call__``. This is useful for situations when something needs to occur prior to a layer starting.

For example, the execution hooks can be used to open connections to remote databases.

.. code:: python

    from typing import Generator

    import psycopg2

    from laminar import Flow, Layer
    from laminar.configurations import hooks

    flow = Flow("Flow")

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            self.cursor.execute("SELECT * FROM table")

        @hooks.execution
        def hello_world(self) -> Generator[None, None, None]:
            with psycopg2.connect("dbname=test user=postgres") as self.connection:
                with self.connection.cursor() as self.cursor:
                    yield


    if __name__ == "__main__":
        flow()

Schedule Hooks
--------------

Schedule hooks run just prior to a ``Layer`` being scheduled for execution. This is useful for situations where the ``Layer`` needs to be configured in a certain way.

For example, the schedule hooks can be used to dynamically adjust resource allocation for a ``Layer``.

.. code:: python

    from typing import Generator

    from laminar import Flow, Layer
    from laminar.configurations import hooks

    flow = Flow("Flow")

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            self.cursor.execute("SELECT * FROM table")

        @hooks.schedule
        def configure_container(self) -> Generator[None, None, None]:
            self.configuration.container.cpu = 4
            self.configuration.container.memory = 2000
            yield

    if __name__ == "__main__":
        flow()

Schedule hooks are particularly powerful when combined with the ``ForEach`` configuration. Each ``ForEach`` split can be configured differently based on the input parameters.

.. code:: python

    from typing import Generator

    from laminar import Flow, Layer
    from laminar.configurations import hooks

    flow = Flow("Flow")

    @flow.register()
    class A(Layer):
        baz: List[str]

        def __call__(self) -> None:
            self.shard(baz=["a", "b", "c"])

    @flow.register(
        foreach=layers.ForEach(parameters=[layers.Parameter(layer=A, attribute="baz")])
    )
    class B(Layer):
        baz: List[str]

        def __call__(self, a: A) -> None:
            print(a.baz, self.configuration.container.memory)

        @hooks.schedule
        def configure_container(self, a: A) -> Generator[None, None, None]:
            assert self.index is not None
            memory = {"a": 1000, "b": 15000, "c": 2000}
            self.configuration.container.memory = memory[a.baz[self.index]]
            yield

    if __name__ == "__main__":
        flow()

.. code:: python

    python main.py

    >>> "a" 1000
    >>> "b" 1500
    >>> "c" 2000

Flow Hooks
----------

Hooks can also be added to a ``Flow`` instead of a ``Layer``. These hooks behave the same way, except they are are invoked on every ``Layer`` within a ``Flow``. This is useful for situations where the same setup/teardown needs to occur on every ``Layer``.

Hooks can be defined on a ``Flow`` by subclassing the ``Flow`` class.

.. code:: python

    # main.py

    from typing import Generator

    from laminar import Flow, Layer
    from laminar.configurations import hooks

    class TestFlow(Flow):
        @hooks.execution
        def hello_world(self) -> Generator[None, None, None]:
            print(f"before {self.name}")
            yield
            print(f"after {self.name}")

    flow = Flow('HelloFlow')

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            print("in A")

    @flow.register()
    class B(Layer):
        def __call__(self, a: A) -> None:
            print("in B")

    if __name__ == "__main__":
        flow()

.. code:: python

    python main.py

    >>> "before A"
    >>> "in A"
    >>> "after A"
    >>> "before B"
    >>> "in B"
    >>> "after B"
