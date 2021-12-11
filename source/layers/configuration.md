# Layer Configuration

## Access

Configurations are a part of the class definition of a `Layer` and are available as an atttribute of the `Layer`. All `Layer` configurations are nested underneath the `Layer.configuration` attribute.

```python
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
```

```python
python main.py

>>> 4 2000
```

```{warning}
If a hook changes a value in `Layer.configuration`, that change will not be reflected in `Layer.__call__`.
```

## Namespace

A `Layer` is simply an execution of work with dependencies and often times layers can perform similar actions as each other. Attempting to register two layers with the same name will raise a `FlowError` even though the two layers are defined separately.

To avoid this a `Layer` may be assigned a namespace that it is a part of, allowing multiple layers with the same name to be registered to the same `Flow`.

```python
# main.py

from laminar import Flow, Layer
from laminar.configurations.layers import Container

flow = Flow("NamespaceFlow")

@flow.register()
class A(Layer, namespace="First"):
    def __call__(self) -> None:
        print(self.name)

@flow.register()
class A(Layer, namespace="Second"):
    def __call__(self, a: A) -> None:
        print(self.name)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> "First.A"
>>> "Second.A"
```

## Retry

Maybe requests to other services can be flaky or maybe you want your `Flow` to be tolerant of AWS EC2 Spot failures. Whatever the reason, there are situations where it is useful for layers to be retried on failure.

`Retry` allows the user to configure the retry policy per layer.

```python
from laminar import Flow, Layer
from laminar.configurations import layers

flow = Flow("RetryFlow")

@flow.register(retry=layers.Retry(attempts=3))
class A(Layer):
    ...
```

`Retry` performs a jittered exponential backoff as the number of attempts increase. Each input to the retry backoff calculation can also be modified.

```python
Retry(attempts=3, delay=0.1, backoff=2, jitter=0.1)
```