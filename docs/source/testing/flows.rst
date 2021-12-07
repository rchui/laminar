Flows
=====

The ``Memory`` datastore and ``Thread`` executor allow flows to be configured for easy testing.

Consider the following linear ``Flow``:

.. code:: python

    from laminar import Flow, Layer
    from laminar.configurations import datastores, executors

    flow = Flow(name="Test", datastore=datastores.Memory(), executor=executors.Thread())


    @flow.register()
    class A(Layer):
        def __call__(self) -> None:
            self.foo = "bar"


    @flow.register()
    class B(Layer):
        def __call__(self, a: A) -> None:
            self.foo = a.foo


    @flow.register()
    class C(Layer):
        def __call__(self, b: B) -> None:
            self.foo = b.foo

Using the results API, it is trivial to execute the flow and make assertions on its outputs.

.. code:: python

    from laminar.utils import unwrap

    def test_flow() -> None:
        execution = flow()

        results = flow.results(unwrap(execution))

        assert results.layer(A).foo == "bar"
        assert results.layer(B).foo == "bar"
        assert results.layer(C).foo == "bar"
