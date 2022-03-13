# Executions

```{warning}
This article covers internal technical details of `Flow` executions. The implementation of a `Flow` may change at any time without warning.
```

## Overview

Laminar `Flow` executions are coordinated across two different actors:

```{eval-rst}
.. list-table::
   :header-rows: 1

   * - Actor
     - Description
   * - Scheduler
     - Compiles the DAG, excecutes layers in a specific order, and polls for completion.
   * - Executor
     - Executes a single ``Layer`` and writes its results to the ``Datastore``.
```

## Anatomy

The following is a rough outline of the call structure of a `Flow` execution.

```{eval-rst}
.. rubric:: Scheduler
```

1. `Flow.__call__`
1. `Flow.schedule` is called and the first set of runnable tasks are identified
1. For each `Layer`, the [entry hook](../advanced/hooks.html#event-hooks) is invoked.
1. The number of splits for each `Layer` is determined.
1. For each `Layer` split, the [submission hook](../advanced/hooks.html#submission-hooks) is invoked.
1. For each `Layer` split, the `Layer` is submitted to the executor it is being run on (thread, docker, batch, etc.)

```{eval-rst}
.. rubric:: Executor
```

1. `Flow.__call__`
1. `Flow.execute` is called and the `Layer` is prepared for execution.
1. The parameters for `Layer.__call__` are prepared.
1. The [execution hook](../advanced/hooks.html#execution-hooks) is invoked.
1. `Layer.__call__`
1. `Layer` artifacts are written to the `Datastore`.

```{eval-rst}
.. rubric:: Scheduler
```

1. The `Layer` is waited on for completion.
1. If the `Layer` fails, the [retry hook](../advanced/hooks.html#retry-hooks) is invoked and the `Layer` retries.
1. The layer's `Record` is written to the `DataStore`.
1. The `Layer` is marked as complete by the scheduler.
1. New runnable layers are identified and scheduled.
