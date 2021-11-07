## Laminar

* [Basics](https://rchui.github.io/laminar/basics)
* [Scaling Up](https://rchui.github.io/laminar/scaling_up)
* [Scaling Out](https://rchui.github.io/laminar/scaling_out)

## Contents

* TOC
{:toc}


## Terminology

* `Flow`: A collection of `Layer` objects that defines the workflow
* `Layer`: A step in the `Flow` workflow that performs an task
* `Archive`: Metadata about an artifact stored for a `Layer`
* `Artifact`: A compressed copy of an assigned `Layer` attribute.

## Dependencies

Defining a `Layer` dependency is as easy as defining a function parameter. In this two `Layer` example, layer `Two` is dependent on layer `One`:

```python
# main.py

from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.layer()
class One(Layer):
    def __call__(self) -> None:
        print(self.name)

@flow.layer()
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

@flow.layer()
class One(Layer):
    def __call__(self) -> None:
        print(self.name)

@flow.layer()
class Two(Layer):
    def __call__(self, one: One) -> None:
        print(self.name)

@flow.layer()
class Three(Layer):
    def __call__(self, two: Two) -> None:
        print(self.name)

@flow.layer()
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

@flow.layer()
class Start(Layer):
    def __call__(self) -> None:
        self.message = "Hello World"
        print(f"Sending the message: {self.message}")

@flow.layer()
class Middle(Layer):
    def __call__(self, start: Start) -> None:
        print(start.message)
        self.message = start.message

@flow.layer()
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
## Sharded Artifacts

Workflows often involve processing large objects which needs to be handled in parts. `laminar` provides `Layer.shard()` to break apart large objects. In downstream steps, the attribute returns an `Accessor` object. An `Accessor` will lazily read sharded artifact values, can be iterated over, and supports direct and slice indexing.

```python
# main.py
from laminar import Flow, Layer

flow = Flow("ShardedFlow")

@flow.layer()
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])

@flow.layer()
class Process(Layer):
    def __call__(self, shard: Shard) -> None:
        print(list(shard.foo))
        print(shard.foo[1])
        print(shard.foo[1:])

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> [1, 2, 3]
>>> 2
>>> [2, 3]
```