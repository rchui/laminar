# Composition

`Flow` composition allows users to define complex workflows without repeating themselves. It enables discreet `Flow`s to be defined that can be executed in isolation and executed in series.

Consider an example with two flows:

```python
from laminar import Flow, Layer
from laminar.components import Parameters
from laminar.configurations import datastores, executors

flow1 = Flow(name="Flow1")


@flow1.register()
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"


flow2 = Flow(name="Flow2")


@flow2.register()
class B(Layer):
    def __call__(self, parameters: Parameters) -> None:
        self.foo = parameters.foo
        print(self.foo)
```

A common scenario might be to execute `Flow1` and feed the results into `Flow2` as parameters. This can be achieved with flow composition.

```python
if __name__ == "__main__":
    flow1().compose(flow=flow2, linker=lambda e: Parameters(foo=e.layer(A).foo))
```

Here we define which `Flow` should be executed after `Flow1` and provider a linker to define how the artifacts of `Flow1` are passed as parameters to `Flow2`.

The linker is of type `Callable[[Execution], Parameters]` where the the parameter `Execution` allows the user to pass through any artifact defined in the preceding `Flow`. This linker takes the value `foo` of layer `A` from `Flow1` and passes it through to `Flow2` as a parameter to be used in layer `B`.

```python
python main.py

>>> "bar"
```

With composition, complex sets of `Flow`s can be linked together to create arbitrarily nested workloads.
