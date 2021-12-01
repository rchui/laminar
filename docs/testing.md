## Laminar

* [Basics](https://rchui.github.io/laminar/basics)
* [Scaling Up](https://rchui.github.io/laminar/scaling_up)
* [Scaling Out](https://rchui.github.io/laminar/scaling_out)
* [Hooks](https://rchui.github.io/laminar/hooks)
* [Flow Configuration](https://rchui.github.io/laminar/flow_configuration)
* [Testing](https://rchui.github.io/laminar/testing)

## Contents

* TOC
{:toc}

## Configuration

The `Memory` datastore and `Thread` executor can be combined to easily test layers and flows. The `Memory` datastore writes all artifacts in an in memory key value store. The `Thread` executor executes layers directly in the main Python process and can all read and write from/to the same `Memory` datastore.

## Layers

Because `Flow` layers are Python classes, their functionality can be tested directly by calling the class constructor and then calling it.

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
# test main.py
from main import A

def test_configure_foo() -> None:
    a = A(foo="bar")
    next(a.configure_foo())
    assert a.foo == "bar.baz"
```
