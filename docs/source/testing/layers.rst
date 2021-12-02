
Layers
======

A ``Layer`` is just a Python classes, so their functionality can be tested directly by calling the class constructor and then calling it.

.. code:: python

    # main.py

    from typing import Generator

    from laminar import Flow, Layer
    from laminar.configurations import datastores, executors, hooks

    flow = Flow('Testflow', datastore=datastores.Memory(), executor=executors.Thread())

    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            self.foo = "bar"

        @hooks.execution
        def configure_foo(self) -> Generator[None, None, None]:
            yield
            self.foo = self.foo + ".baz"

    class B(Layer):
        def __call__(self, a: A) -> None:
            self.foo = a.foo

    if __name__ == "__main__":
        flow()

.. code:: python

    # test_main.py

    from main import A

    def test_A() -> None:
        a = A()
        assert a().foo == "bar"

The ``Layer`` constructor also allows the user to set arbitary key/values to help test layers that depend on other layers.

.. code:: python

    # test_main.py

    from main import A, B

    def test_B() -> None:
        a = A(foo="bar")
        b = B()
        assert b(a).foo == "bar"
