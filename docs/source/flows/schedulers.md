# Schedulers

A ``Flow`` supports multiple backend schedulers which configure how work is scheduled in the workflow.

## Active

By default, flows are configured to use the `Active` scheduler which runs as a process.

The `Active` scheduler:

1. Determines the order that layers should be executed in.
1. Submits layers to the `Executor` for execution.
1. Waits on the layers to complete.

it *actively* manages the task in the workflow until their completion and then exits.

```python
from laminar import Flow
from laminar.configurations import schedulers

flow = Flow("ActiveFlow", scheduler=schedulers.Active())
```

## Passive

```{warning}
Passive schedulers are experimental.
```

`Passive` schedulers don't manage the execution of a workflow. Instead, they compile the flow's directed acyclic graph into a format that can be used by other schedulers to manage the workflow. `Passive` schedulers provide a method for writing flows easily in `laminar` and executing them on another workflow engine.

### AWS Step Functions

```{note}
Under construction
```
