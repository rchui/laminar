# `laminar`

`laminar` is a modern framework for building high performance, easy to learn, fast to code, ready for production workflows.

## Terminology

* `Flow`: A collection of `Layer` objects that defines the workflow
* `Layer`: A step in the `Flow` workflow that performs an action
* `Archive`: Metadata about an artifact stored for a `Layer`
* `Artifact`: A compressed copy of an assigned `Layer` attribute.

## Dependencies

Defining a `Layer` dependency is as easy as defining a function parameter.

```python
# main.py

from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.layer
class One(Layer):
    def __call__(self) -> None:
        print(self.name)

@flow.layer
class Two(Layer):
    def __call__(self, one: One) -> None:
        print(self.name)

@flow.layer
class Three(Layer):
    def __call__(self, one: One) -> None:
        print(self.name)

@flow.layer
class Four(Layer):
    def __call__(self, two: Two, three: Three) -> None:
        print(self.name)
```

```python
python main.py

>>> 'One'
>>> 'Two'
>>> 'Three'
>>> 'Four'
```

## Artifacts

Any value that is set to `self` is automatically saved as an `Archive` and `Artifact` and passed to the next `Layer`. In this way, data is passed logically from one `Layer` to the next.

`laminar` uses a content addressable storage scheme to automatically deduplicate identical data shared between `Layer` objects.

```python
# main.py

from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.layer
class Start(Layer):
    def __call__(self) -> None:
        self.message = "Hello World"
        print(f"Sending the message: {self.message}")

@flow.layer
class Middle(Layer):
    def __call__(self, start: Start) -> None:
        print(start.message)
        self.message = start.message

@flow.layer
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

Workflows often involve processing large objects which needs to be handled in parts. `laminar` provides `Layer.shard()` to break apart large objects. It returns an `Accessor` object that exposes both an `Iterable` interface as well as the ability to index for specific values.

```python
# main.py
from laminar import Flow, Layer

flow = Flow("ShardedFlow")

@flow.layer
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])

@flow.layer
class Process(Layer):
    def __call__(self, shard: Shard) -> None:
        print(list(shard.foo))
        print(shard.foo[1])

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> [1, 2, 3]
>>> 2
```

## ForEach and Grid Search

Modern data science and machine learning techniques often require foreach loops or grid searches of a hyper parameter space. A configuration object `ForEach` combined with `Layer.shard()` makes this simple and logical. `laminar` will calculate all possible combinations for given input parameters, and fans out to compute each separately.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import Configuration, ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2], bar=['a', 'b'])

@flow.layer
class Process(Layer, Configuration(
    foreach=ForEach(
            parameters=[
                Parameter(layer=Shard, attribute="foo"),
                Parameter(layer=Shard, attribute="bar")
            ]
        )
    )
):
    def __call__(self, shard: Shard) -> None:
        print(shard.foo, shard.bar)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 1 'a'
>>> 2 'a'
>>> 1 'b'
>>> 2 'b'
```
