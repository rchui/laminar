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

## Datastores

A `Flow` supports multiple backend data stores. By default, flows are configured to use the `Local` datastore which writes `Flow` artifacts to a location on local disk. Layers in the `Flow` will read from and write to the data store to pass artifacts between layers.

```python
from laminar import flow
from laminar.configurations import datastores

flow = Flow("Datastoreflow", datastore=datastores.Local())
```

## Executors

A `Flow` supports multiple backend executors. By default, flows are configured to use the `Docker` executor which launches each `Layer` registered to a `Flow` in its own docker container. The containers can be configured with the layer's `Container` configuration.

```python
from laminar import Flow
from laminar.configurations import executors, layers

flow = Flow("Executorflow", executor=executors.Docker())

@flow.register(container=layers.Container(cpu=1, memory=1500))
class A(Layer):
    ...
```
