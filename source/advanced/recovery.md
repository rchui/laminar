# Recovery

Dealing with failures is a natural part of developing workflows. For a variety of reasons, workflows may fail and need to be retried or restarted.

## Retry

Maybe requests to other services can be flaky or maybe you want your `Flow` to be tolerant of AWS EC2 Spot failures. Whatever the reason, there are situations where it is useful for layers to be retried on failure.

`Retry` allows the user to configure the retry policy per layer.

```python
from laminar import Flow, Layer
from laminar.configurations import layers

class RetryFlow(Flow):
    ...

@RetryFlow.register(retry=layers.Retry(attempts=3))
class A(Layer):
    ...
```

`Retry` performs a jittered exponential backoff as the number of attempts increase. Each input to the retry backoff calculation can also be modified.

```python
Retry(attempts=3, delay=0.1, backoff=2, jitter=0.1)
```

## Resume

Sometimes a workflow execution fails and the entire flow needs to be re-run. You could choose to run the flow from the beginning, retracing through the graph. However if you want to recover work that has already been performed you would instead want to resume the flow from where it stopped.

```python
execution_id = ...

flow.execution(execution_id).resume()
```

`Flow.Execution.resume` functions very similarly to `Flow.__call__`. It will also start at the beginning of the flow execution, but preemptively skips any layer that has already finished.
