## Laminar

* [Basics](https://rchui.github.io/laminar/basics)
* [Scaling Up](https://rchui.github.io/laminar/scaling_up)
* [Scaling Out](https://rchui.github.io/laminar/scaling_out)
* [Hooks](https://rchui.github.io/laminar/hooks)
* [Flow Configuration](https://rchui.github.io/laminar/flow_configuration)
* [Testing](https://rchui.github.io/laminar/testing)

## Contents

* TOC
{:toc}

## Layer Configuration

Not all layers in a `Flow` need to use the same resources. Some tasks might need a small amount of memory, and others might need a large number of CPUs. `laminar` provides a layer `Container` configuration that can modify the settings of the container the `Layer` is being run in.

```python
from laminar import Flow, Layer
from laminar.configurations.layers import Container

flow = Flow("ConfiguredFlow")

@flow.register(container=Container(cpu=4, memory=2000, workdir="/app"))
class Task(Layer):
    ...
```

A `Container` configuration can also be shared across multiple layers.

```python
from laminar import Flow, Layer
from laminar.configurations.layers import Container

flow = Flow("ConfiguredFlow")

container = Container(cpu=4, memory=2000, workdir="/app")

@flow.register(container=container)
class First(Layer):
    ...

@flow.register(container=container)
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

@flow.register(container=Container(cpu=4, memory=2000, workdir="/app"))
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
