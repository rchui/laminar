Hooks
=====

Hooks are Python class methods and can be tested directly as well.

.. code:: python

    # test main.py

    from main import A

    def test_configure_foo() -> None:
        a = A(foo="bar")
        next(a.configure_foo())
        assert a.foo == "bar.baz"
