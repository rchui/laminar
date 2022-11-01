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

class ParameterFlow(Flow): ...

@ParameterFlow.register
class A(Layer):
    def __call__(self, parameters: Parameters) -> None:
        print(parameters.foo)

if flow := ParameterFlow():
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

Because `Flow.__call__` may take in values as parameters, additional care must be taken to avoid inefficiently calling `Flow.__call__`.

Consider the following example:

```python
import pandas as pd

...

flow(foo=pd.read_csv("path/to/large.csv"))
```

Here we are reading a large CSV into a pandas DataFrame and passing that in as a parameter to the flow. There are two issues:

1. We do not want to read the CSV every time we enter `main.py`.
1. The CSV we need to read may not be present in the image the container is started in.

Instead we can guard against the CSV read with:

```python
import pandas as pd

...

if flow := ParameterFlow():
    flow(foo=pd.read_csv("path/to/large.csv"))
```

`Flow.__bool__` will guard against `Flow.__call__` being called again and also `pd.read_csv`. Instead `Flow.__bool__` will intelligently execute the `Layer` that has been scheduled to run. By only reading data before the `Flow` starts, we can only make our entire `Flow` more efficient.

```{tip}
In general, we always recommend guarding `Flow.__call__` in this way.
```
