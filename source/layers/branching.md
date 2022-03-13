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

Conditions are defined on layers as an entry hook that return a value to indicate whether the `Layer` should be executed or not. Because entry hooks are class methods, users can define multiple hooks and include complex logic to determine conditions.

```{note}
Unlike other hooks, entry hooks can not `yield`. They are evaluated immediately and the return value is evaluated for its "truthiness".
```

```python
import random
from laminar import Flow, Layer
from laminar.configuration import hooks

@flow.register()
class A(Layer):
    def __call__(self) -> None:
        self.foo = random.random()

@flow.register()
class B(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo

    @hooks.entry
    def random_foo(self, a: A) -> bool:
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

In this `Flow`, 50% of the time `B` will be executed and the other 50% it will be skipped. Notice that like `Layer.__call__`, entry hooks can also use layers as parameters in order to evaluate complex conditions.

Consequently, 50% of the time `D` will also be skipped. This is because by default layers will be executed **only if all layers it depends on are executed**. Entire subtrees will potentially be skipped if even if a single `Layer` is set to be skipped.

We can prevent this from occuring by ending the conditional branch:

```python
@flow.register()
class D(Layer):
    def __call__(self, b: B, c: C) -> None:
        ...

    @hooks.entry
    def always_true(self) -> bool:
        return True
```

Now regardless of whether `B` is executed, `D` will always execute. This implies that not only can every layer can have individual execution conditions, but also every `Flow` branch. This enables flows to be extremely flexible in their execution.

But if `D` always executes, how do we know when `B` does?

```{warning}
Conditions are not evaluated to determine `Layer` dependencies. Users are responsible for ensuring that they only use layers that have already been executed.
```

## State

`Layer.state` is a property that returns a `State` object that can evaluate the state that a layer is currently in. `State.finished` will tell you whether or not a `Layer` has been finished. With this logic we can extend `D`.

```python
@flow.register()
class D(Layer):
    def __call__(self, b: B, c: C) -> None:
        self.foo = b.foo if b.state.finished else c.foo

    @hooks.entry
    def always_true(self) -> bool:
        return True
```

`D` now uses the value from `B.foo` if `B` was finished, else it uses the value from `C.foo`.
