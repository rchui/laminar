# Composition

`Flow` composition allows users to define complex workflows without repeating themselves. It enables discreet `Flow`s to be defined that can be executed in isolation and executed in series.

Consider an example with two flows:

```python
from laminar import Flow, Layer
from laminar.components import Parameters

class Flow1(Flow): ...

@Flow1.register
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"

class Flow2(Flow): ...

@Flow2.register
class B(Layer):
    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo
        print(self.foo)
```

```{mermaid}
stateDiagram-v2
    state Flow1 {
        A
    }

    state Flow2 {
        B
    }
```

A common scenario might be to execute `Flow1` and feed the results into `Flow2` as parameters.

## Chaining

This can be achieved with flow chaining.

```python
if flow1 := Flow1():
    flow1().next(
        flow=Flow2(),
        linker=lambda e: Parameters(foo=e.layer(A).foo)
    )
```

```{mermaid}
stateDiagram-v2
    direction LR

    state Flow1 {
        direction LR
        A
    }

    state Flow2 {
        direction LR
        Parameters --> B
    }

    A --> Parameters
```

Here we define which `Flow` should be executed after `Flow1` and provider a linker to define how the artifacts of `Flow1` are passed as parameters to `Flow2`.

The linker is of type `Callable[[Execution], Parameters]` where the the parameter `Execution` allows the user to pass through any artifact defined in the preceding `Flow`. This linker takes the value `foo` of layer `A` from `Flow1` and passes it through to `Flow2` as a parameter to be used in layer `B`.

```python
python main.py

>>> "bar"
```

With composition, complex sets of `Flow`s can be linked together to create arbitrarily nested workloads.


## Inheritance

This can also be achieved with flow inheritance with a small rewrite. Consider the following contrived example:


```python
from laminar import Flow, Layer

class Flow1(Flow): ...

@Flow1.register
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"

class Flow2(Flow): ...

@Flow2.register
class B(Layer):
    def __call__(self, a: A) -> None:
        self.foo = a.foo
        print(self.foo)

class CombinedFlow(Flow1, Flow2):
    ...

if flow := CombinedFlow():
    flow()
```

```{mermaid}
stateDiagram-v2
    direction LR

    state CombinedFlow {
        state Flow1 {
            A
        }

        state Flow2 {
            B
        }
    }
```

Here we define two flows and use class inheritance to merge the two flows together into one single flow. Not only can this be used to chain flows together but also allows you to combine disparate flows into a single execution that will be executed in parallel.

Using chaining and inheritance together enables an extremely expressive way of composing flows together.
