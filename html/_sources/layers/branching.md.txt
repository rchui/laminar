# Branching

Branching allows users to define complex workflows. It also enables parallel executions of non-dependent layers, which can enable significant performance improvements.

## Dependencies

Basic branching can achieved by adding layers as parameters to `Layer.__call__`.

```python
from laminar import Flow, Layer

flow = Flow("HelloFlow")

@flow.register()
class A(Layer):
    def __call__(self) -> None:
        ...

@flow.register()
class B(Layer):
    def __call__(self, a: A) -> None:
        ...

@flow.register()
class C(Layer):
    def __call__(self, a: A) -> None:
        ...
```

When defined in this way, layer `A` will run first and layers `B` and `C` after in parallel because there is no defined dependencies between them.

## Conditions

Conditional branching is a common flow control operation, such as `if ... else ...`, that directs a `Flow` along a subset of paths. As the `Flow` is traversed, conditions are evaluated and paths are chosen.

Conditions are defined on layers in `Layer.__enter__` and returns a `bool` value to indicate whether the `Layer` should be executed or not. Because `Layer.__enter__` is a class method, users can include complex logic to determine conditions.

```python
import random
from laminar import Flow, Layer

@flow.register()
class A(Layer):
    def __call__(self) -> None:
        self.foo = random.random()

@flow.register()
class B(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo

    def __enter__(self, a: A) -> bool:
        return a.foo <= .5

@flow.register()
class C(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo

@flow.register()
class D(Layer):
    def __call__(self, b: B, c: C) -> None:
        ...
```

In this `Flow`, 50% of the time `B` will be executed and the other 50% it will be skipped. Notice that like `Layer.__call__`, `Layer.__enter__` can also use layers as parameters in order to evaluate complex conditions.

Consequently, 50% of the time `D` will also be skipped. This is because by default layers will be executed **only if all layers it depends on are executed**. Entire subtrees will potentially be skipped if even if a single `Layer` is set to be skipped.

We can prevent this from occuring by ending the conditional branch:

```python
@flow.register()
class D(Layer):
    def __call__(self, b: B, c: C) -> None:
        ...

    def __enter__(self) -> bool:
        return True
```

Now regardless of whether `B` is executed, `D` will always execute. This implies that not only can every layer can have individual execution conditions, but also every `Flow` branch. This enables flows to be extremely flexible in their execution.

But if `D` always executes, how do we know when `B` does?

```{warning}
Conditions are not evaluated to determine `Layer` dependencies. Users are responsible for ensuring that they only use layers that have already been executed.
```

## Executed

`Layer.executed` is a property that evaluates whether or not a `Layer` has been executed. With this logic we can extend `D`.

```python
@flow.register()
class D(Layer):
    def __call__(self, b: B, c: C) -> None:
        self.foo = b.foo if b.executed else c.foo

    def __enter__(self) -> bool:
        return True
```

`D` now uses the value from `B.foo` if `B` was executed, else it uses the value from `C.foo`.
