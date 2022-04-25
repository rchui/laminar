# Executors

A `Flow` supports multiple backend executors which configure how work is executed in the workflow.

## Docker

By default, flows are configured to use the `Docker` executor which launches each `Layer` registered to a `Flow` in its own docker container. The launched containers can be configured with the layer's `Container` configuration.

```python
from laminar import Flow
from laminar.configurations import executors, layers

class DockerFlow(Flow):
    ...

@DockerFlow.register(container=layers.Container(cpu=1, memory=1500))
class A(Layer):
    ...

flow = DockerFlow(executor=executors.Docker())
```

## Thread

The `Thread` executor executes layers directly in the main Python process. This is very useful for testing.

```python
from laminar import Flow
from laminar.configurations import executors

flow = Flow(executor=executors.Thread())
```

## AWS.Batch

```{warning}
`AWS.Batch` is experimental.
```

The `AWS.Batch`` executor executes layers on the [AWS Batch](https://aws.amazon.com/batch/) compute service.

```python
from laminar import Flow
from laminar.configurations import executors

flow = Flow(executor=executors.AWS.Batch(job_queue_arn=..., job_role_arn=...))
```
