# Testing

## Flows

The `Memory` datastore and `Thread` executor allow flows to be configured for easy testing.

Consider the following linear `Flow`:

```python
from laminar import Flow, Layer
from laminar.configurations import datastores, executors, serde

datastore = datastores.Memory()

@datastore.protocol(int)
class Int(serde.Protocol):
    def dumps(value: int) -> bytes:
        return str(value).encode()

flow = Flow(name="Test", datastore=datastore, executor=executors.Thread())


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
```

Using the results API, it is trivial to execute the flow and make assertions on its outputs.

```python
from laminar.types import unwrap

def test_flow() -> None:
    execution = flow()

    results = flow.execution(unwrap(execution))

    assert results.layer(A).foo == "bar"
    assert results.layer(B).foo == "bar"
    assert results.layer(C).foo == "bar"
```

## Layers

A `Layer` is a Python classes, so its functionality can be tested directly by calling the class constructor and then calling it.

```python
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
```

```python
# test_main.py

from main import A

def test_A() -> None:
    a = A()
    assert a().foo == "bar"
```

The `Layer` constructor also allows the user to set arbitary key/values to help test layers that depend on other layers.

```python
# test_main.py

from main import A, B

def test_B() -> None:
    a = A(foo="bar")
    b = B()
    assert b(a).foo == "bar"
```

## Hooks

Hooks are Python class methods and can be tested directly as well.

```python
# test_main.py

from main import A

def test_configure_foo() -> None:
    a = A(foo="bar")
    next(a.configure_foo())
    assert a.foo == "bar.baz"
```

## Ser(De)

A `Protocol` is a Python class and can be tested directly.

```python
# test_main.py

from main import Int

def test_int_protocol() -> None:
    assert Int().dumps(1) == b"1"
```
