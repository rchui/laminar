# Hooks

`laminar` supports a hook system for users to extend the existing functionality and dynamically adjust the flow in response to changes that occur at execution time.

Hooks are defined by adding decorators.

```python
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
    def configure_before_after(self) -> Generator[None, None, None]:
        print("before call")
        yield
        print("after call")

```

## Dependencies

Hooks, like other `Layer` functions, can use other layers as dependencies.

```python
@hooks.submission
def configure_container(self, a: A) -> None:
    memory = {"a": 1000, "b": 1500, "c": 2000}
    self.configuration.container.memory = memory[a.foo]
```

The values from those `Layer` dependencies can be used to inform the business logic within each hook.

```{warning}
Hook dependencies are not evaluated to determine `Layer` dependencies. Users are responsible for ensuring that they only use layers that have already been executed.
```

## Multiple Hooks

Any number of each type of hook can be defined for a `Layer`. Here is a replication of `configure_before_after` from the above execution hook with two hooks:

```python
import random
from typing import Generator
from laminar import Flow, Layer
from laminar.configurations import hooks

flow = Flow("Flow")

@flow.register()
class A(Layer):
    def __call__(self) -> None:
        print("in call")

    @hooks.execution
    def configure_entry_1(self) -> None:
        print("before call")

    @hooks.execution
    def configure_entry_2(self) -> Generator[None, None, None]:
        yield
        print("after call")
```

Hooks of the same type are executed in the order that they are defined in the `Layer`. Using multiple hooks allows for deep and dynamic customization of the entire `Layer` lifecycle.

## Types

### Event Hooks

Event hooks are Python generators or functions that can perform actions before and after events occur within the flow. A hook defined as a generator will yield until the `Layer` has completed executing before finishing. A hook defined as a function will immediately return before the `Layer` has been executed.

#### Execution Hooks

Execution hooks run just prior to the invocation of `Layer.__call__`. This is useful for situations when something needs to occur prior to a layer starting.

For example, the execution hooks can be used to open connections to remote databases.

```python
from typing import Generator

import psycopg2

from laminar import Flow, Layer
from laminar.configurations import hooks

flow = Flow("Flow")

@flow.register()
class A(Layer):
    def __call__(self) -> None:
        self.cursor.execute("SELECT * FROM <table>")

    @hooks.execution
    def hello_world(self) -> Generator[None, None, None]:
        with psycopg2.connect("dbname=test user=postgres") as self.connection:
            with self.connection.cursor() as self.cursor:
                yield


if __name__ == "__main__":
    flow()
```

```{note}
Execution hooks are invoked on the `Layer` executor.
```

#### Retry Hooks

Retry hooks run just prior to waiting for a `Layer`'s retry backoff. This is useful for situations where the `Layer` needs to be adjusted in response to a failure.

For example, here we double the requested memory every time the `Layer` needs to retry.

```python
from laminar import Flow, Layer
from laminar.configurations import hooks

flow = Flow("Flow")

@flow.register()
class A(Layer):
    @hooks.retry
    def configure_container(self) -> None:
        self.configuration.container.memory = self.configuration.container.memory * 2

if __name__ == "__main__":
    flow()
```

```{note}
Retry hooks are invoked on the `Flow` scheduler.
```

#### Submission Hooks

Submission hooks run just prior to a `Layer` being submitted for execution. This is useful for situations where the `Layer` needs to be configured in a certain way.

For example, the submission hooks can be used to dynamically adjust resource allocation for a `Layer`.

```python
from typing import Generator

from laminar import Flow, Layer
from laminar.configurations import hooks

flow = Flow("Flow")

@flow.register()
class A(Layer):
    @hooks.submission
    def configure_container(self) -> None:
        self.configuration.container.cpu = 4
        self.configuration.container.memory = 2000

if __name__ == "__main__":
    flow()
```

Submission hooks are particularly powerful when combined with the `ForEach` configuration. Each `ForEach` split can be configured differently based on the input parameters.

```python
from laminar import Flow, Layer
from laminar.configurations import hooks
from laminar.types import unwrap

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

    @hooks.submission
    def configure_container(self, a: A) -> None:
        memory = {"a": 1000, "b": 1500, "c": 2000}
        self.configuration.container.memory = memory[a.baz[unwrap(self.index)]]

if __name__ == "__main__":
    flow()
```

```python
python main.py

>>> "a" 1000
>>> "b" 1500
>>> "c" 2000
```

```{note}
Submission hooks are invoked on the `Flow` scheduler.
```

### Condition Hooks

Condition hooks are Python functions that return values that are used to evaluate the state of the `Flow` at runtime. The returned values are used to make informed decisions what the `Flow` should do next.

##### Entry Hooks

Refer to the documentation on [conditional branching](../layers/branching.html#conditions) for an explanation of how entry hooks work.

## Flow Hooks

Hooks can also be added to a `Flow` instead of a `Layer`. These hooks behave the same way, except they are are invoked on every `Layer` within a `Flow`. This is useful for situations where the same setup/teardown needs to occur on every `Layer`.

Hooks can be defined on a `Flow` by subclassing the `Flow` class.

```python
# main.py

from typing import Generator

from laminar import Flow, Layer
from laminar.configurations import hooks

class HelloFlow(Flow):
    @hooks.execution
    def hello_world(self) -> Generator[None, None, None]:
        print(f"before {self.name}")
        yield
        print(f"after {self.name}")

flow = HelloFlow(name='HelloFlow')

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
```

```python
python main.py

>>> "before A"
>>> "in A"
>>> "after A"
>>> "before B"
>>> "in B"
>>> "after B"
```
