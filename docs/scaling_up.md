## Laminar

* [Basics](https://rchui.github.io/laminar/basics)
* [Scaling Up](https://rchui.github.io/laminar/scaling_up)
* [Scaling Out](https://rchui.github.io/laminar/scaling_out)

## Contents

* TOC
{:toc}

## Layer Configuration

Not all layers in a `Flow` need to use the same resources. Some tasks might need a small amount of memory, and others might need a large number of CPUs. `laminar` provides a layer `Container` configuration that can modify the settings of the container the `Layer` is being run in.

```python
from laminar import Flow, Layer
from laminar.configurations.layers import Container

flow = Flow("ConfiguredFlow")

@flow.layer(container=Container(cpu=4, memory=2000, workdir="/app"))
class Task(Layer):
    ...
```

A `Container` configuration can also be shared across multiple layers.

```python
from laminar import Flow, Layer
from laminar.configurations.layers import Container

flow = Flow("ConfiguredFlow")

container = Container(cpu=4, memory=2000, workdir="/app")

@flow.layer(container=container)
class First(Layer):
    ...

@flow.layer(container=container)
class Second(Layer):
    ...
```

## Configuration Access

Configurations are a part of the class definition of a `Layer` and thus are available as an atttribute of the `Layer`. All `Layer` configurations are nested underneath the `Layer.configuration` attribute.

```python
# main.py
from laminar import Flow, Layer
from laminar.configurations.layers import Container

flow = Flow("ConfiguredFlow")

@flow.layer(container=Container(cpu=4, memory=2000, workdir="/app"))
class Task(Layer):
    def __call__(self) -> None:
        print(self.configuration.container.cpu, self.configuration.container.memory)

if __name__ == '__main__':
    flow()
```

```python
python main.py

>>> 4 2000
```

## Dynamic Configuration

Not executions of the same flow need the same resources. Even if the data is being processed in the same way, the amount of data can affect how much cpu/memory needs to be allocated to accomplish the given task.

The `Container` configuration can be subclassed and the `__call__` function overwritten to provide a dynamic configuration based off of the outputs of a previous step. `__call__` follows the same parameter rules as a `Layer` does and can also pull in arbitrary layers as inputs.

```python
from laminar import Flow, Layer
from laminar.configurations.layers import Container

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

@flow.layer(container=ConfiguredContainer())
class Configured(Layer):
    ...

if __name__ == "__main__":
    flow()
```

Prior to the execution of the `Configured` layer, `ConfiguredContainer` will be provided layer `One` as an input parameter to `__call__` to dynamically overwrite values on itself.
