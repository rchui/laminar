# Parameters

Flows can be parameterized so that the same logic can be executed multiple times with different inputs.

```{tip}
It may be helpful to read [Technical Details: Execution](../technical/executions) to get a better understanding of why execution guards and multiple entrypoints are useful.
```

## Passing Values

There are two parts involved in parameterizing a `Flow`.

1. Keyword arguments passed to `Flow.__call__` are written to the flow's `Datastore`.
1. A special layer `Parameters` is automatically registered to every `Flow` and is able to reference any `Flow` parameter with the same behavior as any other `Layer`.

```python
# main.py

from laminar import Flow, Layer
from laminar.components import Parameters

class ParameterFlow(Flow):
    ...

@ParameterFlow.register()
class A(Layer):
    def __call__(self, parameters: Parameters) -> None:
        print(parameters.foo)

if __name__ == "__main__":
    flow = ParameterFlow()
    flow(foo="bar")
```

```{mermaid}
stateDiagram-v2
    state ParameterFlow {
        direction LR
        Parameters --> A
    }
```

```python
python main.py

>>> "bar"
```

`Parameters` can be used as a parameter like any other `Layer` in a `Flow`. It will automatically reference artifacts in the flow's `Datastore` and return the corresponding values. In this way, any arbitrary parameter can be passed into the `Flow`.

## Execution Guard

Because `Flow.__call__` is the entrypoint for both scheduling a `Flow` and executing a `Layer`, additional care must be taken to avoid inefficiently calling `Flow.__call__`.

Consider the following example:

```python
import pandas as pd

...

if __name__ == "__main__":
    flow(foo=pd.read_csv("path/to/large.csv"))
```

Here we are reading a large CSV into a pandas DataFrame and passing that in as a parameter to the flow. There are two issues:

1. We do not want to read the CSV every time we enter `main.py`.
1. The CSV we need to read may not be present in the image the container is started in.

`Flow.execution` is a property that returns an `Execution` object that can evaluate the state of a `Flow`. `Execution.running` will tell you whether or not the `Flow` is running. With this, we can guard against the CSV read:

```python
import pandas as pd

...

if __name__ == "__main__":
    # Scheduling a Flow
    flow() if flow.execution.running else flow(foo=pd.read_csv("path/to/large.csv"))
```

By only reading data before the `Flow` starts, we can only make our entire `Flow` more efficient.

## Multiple Entrypoints

An alternative approach involves setting up multiple entrypoints. Define a flow with an invocation of `Flow.__call__`:

```python
# main.py

from laminar import Flow
from laminar.configurations import layers

class ParameterFlow(Flow):
    ...

@ParameterFlow.register(container=layers.Contaienr(command="python execution.py"))
class A(Layer):
    def __call__(self, parameters: Parameters) -> None:
        print(parameters.foo)
```

In one entrypoint add the parameters to `Flow.__call__`:

```python
# parameters.py

import pandas as pd

from main import flow

if __name__ == "__main__":
    flow(foo=pd.read_csv("path/to/large.csv"))
```

In another invoke `Flow.__call__` without parameters:

```python
# execution.py

from main import flow

if __name__ == "__main__":
    flow()
```

To execute the `Flow`:

```python
python parameters.py
```

Here we guard against always loading the CSV by using separate entrypoints and configuring our container to use the `execution.py` entrypoint instead of the `parameters.py` entrypoin.
