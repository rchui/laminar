# Parameters

Flows can be parameterized so that the same logic can be executed multiple times with different inputs.

```{note}
It may be helpful to read [Technical Details: Execution](../technical/executions) to get a better understanding of why execution guards and multiple entrypoints are useful.
```

## Passing Values

There are two parts involved in parameterizing a `Flow`.

1. Keyword arguments passed to `Flow.parameters` are written to the flow's `Datastore`.
1. A special layer `Parameters` is automatically registered to every `Flow` and is able to reference any `Flow` parameter with the same behavior as any other `Layer`.

```python
# main.py

from laminar import Flow, Layer
from laminar.components import Parameters

flow = Flow("ParameterFlow")

@flow.register()
class A(Layer):
    def __call__(self, parameters: Parameters) -> None:
        print(parameters.foo)

if __name__ == "__main__":
    execution = flow.parameters(foo="bar")
    flow(execution=execution)
```

```python
python main.py

>>> "bar"
```

`Parameters` can be used as a parameter like any other `Layer` in a `Flow`. It will automatically reference artifacts in the flow's `Datastore` and return the corresponding values. In this way, any arbitrary parameter can be passed into the `Flow`.

## Execution Guard

Because `Flow.__call__` is the entrypoint for both scheduling a `Flow` and executing a `Layer`, additional care must be taken to avoid inefficiently calling `Flow.parameters`.

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

To avoid this we can guard the CSV read with the `current` object.

```python
import pandas as pd

from laminar.settings import current

...

if __name__ == "__main__":

    execution = None

    # Scheduling a Flow
    if not current.execution.id:
        execution = flow.parameters(foo=pd.read_csv("path/to/large.csv"))

    flow(execution=execution)
```

By guarding against layer execution, we can only make our entire `Flow` more efficient.

## Multiple Entrypoints

An alternative approach involves setting up multiple entrypoints. Define a flow with an invocation of `Flow.__call__`:

```python
# main.py

from laminar import Flow
from laminar.configurations import layers

flow = Flow("ParameterFlow")

@flow.register(container=layers.Contaienr(command="python execution.py"))
class A(Layer):
    def __call__(self, parameters: Parameters) -> None:
        print(parameters.foo)
```

In one entrypoint add the parameters to `Flow.parameters`:

```python
# parameters.py

import pandas as pd

from main import flow

if __name__ == "__main__":
    execution = flow.parameters(foo=pd.read_csv("path/to/large.csv"))
    flow(execution=execution)
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
