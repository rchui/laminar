## Laminar

* [Basics](https://rchui.github.io/laminar/basics)
* [Scaling Up](https://rchui.github.io/laminar/scaling_up)
* [Scaling Out](https://rchui.github.io/laminar/scaling_out)

## Contents

* TOC
{:toc}


## ForEach Loops

Often it is better to break up a problem across many tasks instead of processing it all in one task. The `ForEach` layer configuration combined with `Layer.shard()` makes this a simple process.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer()
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2])

@flow.layer()
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

`laminar` will infer from the defined `Parameter` layer and shard, how many tasks to create in the `Process` layer. Any `Layer` attribute can be defined as a `ForEach` parameter. Even ones that have not been sharded.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer()
class Shard(Layer):
    def __call__(self) -> None:
        self.bar = "a"
        self.shard(foo=[1, 2])

@flow.layer()
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

`laminar` will infer that an attribute is not sharded and supply that value to each `ForEach` task.

## Grid Search

`ForEach` can handle arbitrary numbers of `Parameter` inputs. When provided with more than one `Parameter`, `ForEach` will create a task for each permutation of the `ForEach` parameters.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer()
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3], bar=["a", "b"])

@flow.layer(
    foreach=ForEach(
        parameters=[
            Parameter(layer=Shard, attribute="foo"),
            Parameter(layer=Shard, attribute="bar")
        ]
    )
)
class Process(Layer):
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

@flow.layer()
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2])

@flow.layer(
    foreach=ForEach(
        parameters=[Parameter(layer=Shard, attribute="foo")]
    )
)
class Process(Layer):
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
from laminar.configurations.layers import ForEach, Parameters

flow = Flow("ShardedFlow")

@flow.layer()
class Shard(Layer):
    def __call__(self) -> None:
        self.shard(foo=[1, 2, 3])

@flow.layer(foreach=ForEach(parameters=[Parameter(layer=Shard, attribute="foo")]))
class First(Layer):
    def __call__(self, shard: Shard) -> None:
        print('First', shard.foo)
        self.foo = shard.foo

@flow.layer(foreach=ForEach(parameters=[Parameter(layer=First, attribute="foo", index=None)]))
class Second(Layer):
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

By default an unset `Parameter.index` will read from `Parameter(index=0)`.
