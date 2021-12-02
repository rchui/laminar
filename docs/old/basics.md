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

## Registering Layers

A `Flow` is a collection of Layers that define a workflow and perform tasks. A `Layer` must be registered with a `Flow` before it can be used in the `Flow`:

```python
from laminar import Flow, Layer

flow = Flow("RegisterFLow")

@flow.register()
class One(Layer):
    ...

@flow.register():
class Two(Layer):
    ...
```

A `Layer` can be registered to multiple flows:

```python
from laminar import Flow, Layer

flow1 = Flow("Flow1")
flow2 = Flow("Flow2")

@flow1.register()
@flow2.register()
class One(Layer):
    ...

@flow1.register():
@flow2.register()
class Two(Layer):
    ...
```

## Executing Flows

A `Flow` can be triggered to run all the registered layers by calling it. A `Layer.__call__` can be overriden to define what actions the `Layer` should perform.

```python
from laminar import Flow, Layer

flow = Flow("TriggerFlow")

@flow.register()
class A(Layer):
    def __call__(self) -> None:
        print("hello world")

if __name__ == "__main__":
    flow()
```

```python
>>> "hello world"
```

## Dependencies

Defining a `Layer` dependency is done by adding function parameters to `__call__`. A registered `Layer` is inferred from the type annotation to determine which Layers depend on which other Layers. In this two `Layer` example, layer `Two` is dependent on layer `One`:

```python
# main.py

from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.register()
class One(Layer):
    def __call__(self) -> None:
        print(self.name)

@flow.register()
class Two(Layer):
    def __call__(self, one: One) -> None:
        print(self.name)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 'One'
>>> 'Two'
```

Dependencies can be arbitrarily complex but must represent a directed acyclic graph. Any `Layer` can have a dependency on any other `Layer`, without cycles. Consider this extended example:

```python
# main.py

from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.register()
class One(Layer):
    def __call__(self) -> None:
        print(self.name)

@flow.register()
class Two(Layer):
    def __call__(self, one: One) -> None:
        print(self.name)

@flow.register()
class Three(Layer):
    def __call__(self, two: Two) -> None:
        print(self.name)

@flow.register()
class Four(Layer):
    def __call__(self, one: One, three: Three) -> None:
        print(self.name)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 'One'
>>> 'Two'
>>> 'Three'
>>> 'Four'
```

Here `Two` waits on `One`, `Three` waits on `Two`, and `Four` waits on `One` and `Three` to complete before running.

## Artifacts

Any value that is set to `self` is automatically saved as an `Archive` and `Artifact` and passed to the next `Layer`. In this way, data is passed logically from one `Layer` to the next and are referenced directly using the `dot` attribute notation.

```python
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

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> "Sending the message: Hello World"
>>> "Hello World"
>>> "Sent message: Hello World"
```
