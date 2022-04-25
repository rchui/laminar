# Results

`laminar` provides an API for programmatically inspecting results of all past runs.

## Object Hierarchy

The object hierarchy is the same of that for the runtime `Flow` and `Layer` objects. In fact the results API uses the same objects as those used at runtime (with caveats).

```{eval-rst}
.. list-table::
   :header-rows: 1

   * - Hierarchy
     - Object
     - Description
   * - 1
     - ``Flow``
     - A collection of ``Layer`` objects that are run in sequence as a workflow.
   * - 2
     - ``Execution``
     - A single run of a ``Flow``.
   * - 3
     - ``Layer``
     - A unit of work in an ``Execution`` that performs actions.
   * - 4
     - ``Archive``
     - Metadata for an artifact.
   * - 5
     - ``Artifact``
     - A pickled and gzipped Python object.
```

## Accessing Flows

Flows can be accessed by importing them from their definition file:

```python
# main.py

from laminar import Flow, Layer

class ResultFlow(Flow):
  ...

@ResultFlow.register()
class A(Layer):
    def __call__(self) -> None:
        self.foo = "bar"

if __name__ == "__main__":
    flow = ResultFlow()
    flow()
```

`Flow.execution()` will configure the `Flow` so that it is ready to read from the configured datastore.

```python
from main import flow

flow.execution("21lYX2jVgfbdYqyuEPr8kWkf3vp")
>>> Execution(id="21lYX2jVgfbdYqyuEPr8kWkf3vp")
```

## Accessing Layers

`Execution.layer()` exposes all layers registered to the `Flow`. Layers returned from `Execution.layer()` will be configured to read from the configured `Flow` datastore.

```python
from main import A, flow

flow.execution("21lYX2jVgfbdYqyuEPr8kWkf3vp").layer(A)
>>> A(flow=ResultsFlow(execution=Execution(id="21lYX2jVgfbdYqyuEPr8kWkf3vp")), ...)
```

Because layers derive their datastore from the `Flow` they are registered to, only layers from `Execution.layer()` will be able to access the datastore correctly.

## Accessing Artifacts

A `Layer` from `Execution.layer()` behaves (almost) like a `Layer` at runtime. Artifacts from the `Layer` can be accessed as you would normally.

```python
from main import A, flow

flow.execution("21lYX2jVgfbdYqyuEPr8kWkf3vp").layer(A).foo
>>> "bar"
```

## Discovery

You may not always know apriori what executions have been made, layers are registered, or artifacts exist. The configured `Datastore` has multiple `list_*` convenience functions to aid in that discovery.

```python
from main import flow

# Access the configured datastore
datastore = flow.configuration.datastore

# List executions
datastore.list_executions(flow=flow)
>>> [
  ResultsFlow(execution=Execution(id="21lYX2jVgfbdYqyuEPr8kWkf3vp")),
  ...
]

# List layers
execution = flow.execution("21lYX2jVgfbdYqyuEPr8kWkf3vp")
datastore.list_layers(execution=execution)
>>> [
  A(flow=ResultsFlow(execution=Execution(id="21lYX2jVgfbdYqyuEPr8kWkf3vp"))),
  ...
]

# List artifacts
from main import A

layer = flow.execution("...").layer(A)
datastore.list_artifacts(layer=layer)
>>> [
  "foo",
  ...
]
```
