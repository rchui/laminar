# Scaling Out

## Sharded Artifacts

Workflows often involve processing large objects which needs to be handled in parts. `laminar` provides `Layer.shard()` to break apart large objects. In downstream steps, the attribute returns an `Accessor` object. An `Accessor` will lazily read sharded artifact values, can be iterated over, and supports direct and slice indexing.

```python
# main.py

from laminar import Flow, Layer

class ShardedFlow(Flow): ...

@ShardedFlow.register
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])

@ShardedFlow.register
class Process(Layer):
    def __call__(self, shard: Shard) -> None:
        print(list(shard.foo))
        print(shard.foo[1])
        print(shard.foo[1:])

if flow := ShardedFlow():
    flow()
```

```{mermaid}
stateDiagram-v2
    state ShardedFlow {
        direction LR
        Shard --> Process
    }
```

```python
python main.py

>>> [1, 2, 3]
>>> 2
>>> [2, 3]
```

```{note}
A sharded object is expected to be `Iterable`. Each value returned by `__iter__` will be sharded separately.
```

## ForEach Loops

Often it is better to break up a problem across many tasks instead of processing it all in one task. The `ForEach` layer configuration combined with `Layer.shard()` makes this a simple process.

```python
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

class ForeachFlow(Flow): ...

@ForeachFlow.register
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2])

@ForeachFlow.register(
    foreach=ForEach(
        parameters=[Parameter(layer=Shard, attribute="foo")]
    )
)
class Process(Layer):
    def __call__(self, shard: Shard) -> None:
        print(self.index, shard.foo)

if flow := ForeachFlow():
    flow()
```

```{mermaid}
stateDiagram-v2
    state ForeachFlow {
        direction LR

        state fork <<fork>>
            Shard --> fork

        fork --> Process[0]
        fork --> Process[1]
        fork --> Process[...]
        fork --> Process[N]
    }
```

```python
python main.py

>>> 0 1
>>> 1 2
```

`laminar` will infer from the defined `Parameter` the `Layer` and attribute to fork over. The number of tasks to create in the `Process` layer is determined by the size of `Parameter`. Any `Layer` attribute can be defined as a `ForEach` parameter, including ones that have not been
sharded.

```python
# main.py

from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

class ForeachFlow(Flow): ...

@ForeachFlow.register
class Shard(Layer):
    def __call__(self) -> None:
        self.bar = "a"
        self.shard(foo=[1, 2])

@ForeachFlow.register(
    foreach=ForEach(
        parameters=[
            Parameter(layer=Shard, attribute="foo"),
            Parameter(layer=Shard, attribute="bar")
        ]
    )
)
class Process(Layer):
    def __call__(self, shard: Shard) -> None:
        print(self.index, shard.foo, shard.bar)

if flow := ForeachFlow():
    flow()
```

```{mermaid}
stateDiagram-v2
    state ForeachFlow {
        direction LR

        state fork <<fork>>
            Shard --> fork

        fork --> Process[0,0]
        fork --> Process[0,1]
        fork --> Process[0,...]
        fork --> Process[0,N]
    }
```

```python
python main.py

>>> 0 1 "a"
>>> 1 2 "a"
```

`laminar` will infer that an attribute is not sharded and supply that value to each `ForEach` task.

## Grid Search

`ForEach` can handle arbitrary numbers of `Parameter` inputs. When provided with more than one `Parameter`, `ForEach` will execute the `Layer` for each permutation of the `ForEach` parameters.

```python
# main.py

from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

class GridFlow(Flow): ...

@GridFlow.register
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3], bar=["a", "b"])

@GridFlow.register(
    foreach=ForEach(
        parameters=[
            Parameter(layer=Shard, attribute="foo"),
            Parameter(layer=Shard, attribute="bar")
        ]
    )
)
class Process(Layer):
    def __call__(self, shard: Shard) -> None:
        print(self.index, shard.foo, shard.bar)

if flow := GridFlow():
    flow()
```

```{mermaid}
stateDiagram-v2
    state GridFlow {
        direction LR

        state fork <<fork>>
            Shard --> fork

        fork --> Process[0,0]
        fork --> Process[0,1]
        fork --> Process[...,...]
        fork --> Process[M,N]
    }
```

```python
python main.py

>>> 0 1 "a"
>>> 1 2 "a"
>>> 2 3 "a"
>>> 3 1 "b"
>>> 4 2 "b"
>>> 5 3 "b"
```

`laminar` infers that the `ForEach` is iterating over two sharded attributes. It generates the cartesian product of each attribute and launches a `ForEach` task to handle each resulting fork.

## ForEach Joins

A `ForEach` layer does not need a special join step in order to merge branch values back together. A `ForEach` layer used as an input for a downstream layer will have attributes that follow the same rules as if it was created using `Layer.shard()` by returning an `Accessor` mapped to each `ForEach` task.

```python
# main.py

from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

class JoinFlow(Flow): ...

@JoinFlow.register
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2])

@JoinFlow.register(
    foreach=ForEach(
        parameters=[Parameter(layer=Shard, attribute="foo")]
    )
)
class Process(Layer):
    def __call__(self, shard: Shard) -> None:
        self.foo = shard.foo

@JoinFlow.layer
class Join(Layer):
    def __call__(self, process: Process) -> None:
        print(list(process.foo))
        print(process.foo[1])

if flow := JoinFlow():
    flow()
```

```{mermaid}
stateDiagram-v2
    state JoinFlow {
        direction LR

        state fork <<fork>>
            Shard --> fork

        fork --> Process[0]
        fork --> Process[1]
        fork --> Process[...]
        fork --> Process[N]

        state join <<join>>
            Process[0] --> join
            Process[1] --> join
            Process[...] --> join
            Process[N] --> join

        join --> Join
    }
```

```python
python main.py

>>> [1, 2]
>>> 2
```

Like sharded artifacts, the attribute accessor for `ForEach` artifacts will lazily read sharded values, can be iterated over, indexed, and sliced as necessary.

## Chained ForEach

It is common to performed multiple foreach loops in a row, where each value produced by a foreach task is passed to another foreach task. You can define `Parameter(index=None)` in subsequent `ForEach` to create a `1:1` mapping of one foreach to another.

```python
# main.py

from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

class ChainedFlow(Flow): ...

@ChainedFlow.register
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])

@ChainedFlow.register(foreach=ForEach(parameters=[Parameter(layer=Shard, attribute="foo")]))
class First(Layer):
    def __call__(self, shard: Shard) -> None:
        print(self.index, 'First', shard.foo)
        self.foo = shard.foo

@ChainedFlow.register(
    foreach=ForEach(parameters=[Parameter(layer=First, attribute="foo", index=None)])
)
class Second(Layer):
    def __call__(self, first: First) -> None:
        print(self.index, 'Second', first.foo)

if flow := ChainedFlow():
    flow()
```

```{mermaid}
stateDiagram-v2
    state ChainedFlow {
        direction LR

        state fork <<fork>>
            Shard --> fork

        fork --> First[0]
        fork --> First[1]
        fork --> First[...]
        fork --> First[N]

        First[0] --> Second[0]
        First[1] --> Second[1]
        First[...] --> Second[...]
        First[N] --> Second[N]
    }
```

```python
python main.py

>>> 0 'First' 1
>>> 1 'First' 2
>>> 2 'First' 3
>>> 0 'Second' 1
>>> 1 'Second' 2
>>> 2 'Second' 3
```

This allows us to perform a series of fan-out operations in a row without needing to join until it is necessary.
