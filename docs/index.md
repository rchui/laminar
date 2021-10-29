## Laminar

> slow is smooth, and smooth is fast

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

@flow.layer
class One(Layer):
    def __call__(self) -> None:
        print(self.name)

@flow.layer
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
    def __call__(self, two: Two) -> None:
        print(self.name)

@flow.layer
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

Here layer `Four` waits on layers `One` and `Three` to complete before running.

## Artifacts

Any value that is set to `self` is automatically saved as an `Archive` and `Artifact` and passed to the next `Layer`. In this way, data is passed logically from one `Layer` to the next and are referenced directly using the `dot` attribute notation.

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

Workflows often involve processing large objects which needs to be handled in parts. `laminar` provides `Layer.shard()` to break apart large objects. In downstream steps, the attribute returns an `Accessor` object that can accessed by index or iterated over.

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

## ForEach Loops

Often it is better to break up a problem across many tasks instead of processing it all in one task. The `ForEach` layer configuration combined with `Layer.shard()` makes this a simple process.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2])

@flow.layer
class Process(
    Layer,
    foreach=ForEach(
        parameters=[Parameter(layer=Shard, attribute="foo")]
    )
):
    def __call__(self, shard: Shard) -> None:
        print(shard.foo)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 1
>>> 2
```

`laminar` will infer from the defined `Parameter` layer and shard, how many tasks to create in the `Process` layer. Any `Layer` attribute can be defined as a `ForEach` parameter.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer
class Shard(Layer):
    def __call__(self) -> None:
        self.bar = "a"
        self.shard(foo=[1, 2])

@flow.layer
class Process(
    Layer,
    foreach=ForEach(
        parameters=[
            Parameter(layer=Shard, attribute="foo"),
            Parameter(layer=Shard, attribute="bar")
        ]
    )
):
    def __call__(self, shard: Shard) -> None:
        print(shard.foo, shard.bar)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 1 "a"
>>> 2 "a"
```

## Grid Search

`laminar` will infer that an attribute is not sharded and supply that value to each `ForEach` task. Notice that `ForEach` can handle arbitrary numbers of `Parameter` inputs. When provided with more than one `Parameter`, `ForEach` will create a task for each permutation of the `ForEach` parameters.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3], bar=["a", "b"])

@flow.layer
class Process(
    Layer,
    foreach=ForEach(
        parameters=[
            Parameter(layer=Shard, attribute="foo"),
            Parameter(layer=Shard, attribute="bar")
        ]
    )
):
    def __call__(self, shard: Shard) -> None:
        print(shard.foo, shard.bar)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 1 "a"
>>> 2 "a"
>>> 3 "a"
>>> 1 "b"
>>> 2 "b"
>>> 3 "b"
```

## ForEach Joins

A `ForEach` layer does not need a special join step in order to merge branch values back together. A `ForEach` layer used as an input for a downstream layer will have attributes that follow the same rules as if it was created using `Layer.shard()` by returning an `Accessor` mapped to each `ForEach` task.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2])

@flow.layer
class Process(
    Layer,
    foreach=ForEach(
        parameters=[Parameter(layer=Shard, attribute="foo")]
    )
):
    def __call__(self, shard: Shard) -> None:
        self.foo = shard.foo

@flow.layer
class Join(Layer):
    def __call__(self, process: Process) -> None:
        print(list(process.foo))
        print(process.foo[1])

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> [1, 2]
>>> 2
```

## Chained ForEach

It is common to performed multiple foreach loops in a row, where each value produced by a foreach is passed to another foreach. You can define `Parameter(index=None)` in subsequent `ForEach` to create a `1:1` mapping of one foreach to another.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import Configuration, ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])

@flow.layer
class First(
    Layer,
    foreach=ForEach(parameters=[Parameter(layer=Shard, attribute="foo")])
):
    def __call__(self, shard: Shard) -> None:
        print('First', shard.foo)
        self.foo = shard.foo

@flow.layer
class Second(
    Layer,
    foreach=ForEach(parameters=[Parameter(layer=First, attribute="foo", index=None)])
):
    def __call__(self, first: First) -> None:
        print('Second', first.foo)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 'First' 1
>>> 'First' 2
>>> 'First' 3
>>> 'Second' 1
>>> 'Second' 2
>>> 'Second' 3
```

## Dynamic Layer Configuration

Not all workloads need the same resources. Even if the data is being processed in the same way, the amount of data can affect how much cpu/memory needs to be allocated to accomplish the given task.

The `Container` configuration can be subclassed and the `__call__` function overwritten to provide a dynamic configuration based off of the outputs of a previous step. `__call__` follows the same parameter rules as a `Layer` does and can also pull in arbitrary layers as inputs.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import Configuration, Container

flow = Flow("ConfiguredFlow")

@flow.layer
class Start(Layer):
    def __call__(self) -> None:
        self.foo = True

class ConfiguredContainer(Container):
    def __call__(self, one: One) -> None:
        if one.foo:
            self.cpu = 2
        else:
            self.memory = 5000

@flow.layer
class Configured(Layer, container = ConfiguredContainer()):
    ...

if __name__ == "__main__":
    flow()
```

Prior to the execution of the `Configured` layer, `ConfiguredContainer` will pull in layer `One` as an input parameter and process `__call__` to dynamically overwrite values on itself.

