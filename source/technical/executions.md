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
     - Executes a single `Layer` and writes its results to the `Datastore`.
```

## Anatomy

The following is a rough outline of the call structure of a `Flow` execution.

```{eval-rst}
.. rubric:: Scheduler
```

1. `Flow.__call__`
2. `Flow.schedule` is called and the first set of runnable tasks are identified
3. The number of splits for each `Layer` is determined.
4. For each `Layer` split, the `submit hook <../advanced/hooks.html#submit-hooks>`_ is invoked.
5. For each `Layer` split, the `Layer` is submitted to the executor it is being run on (thread, docker, batch, etc.)

```{eval-rst}
.. rubric:: Executor
```

1. `Flow.__call__`
2. `Flow.execute` is called and the `Layer` is prepared for execution.
3. The parameters for `Layer.__call__` are prepared.
4. The `execution hook <../advanced/hooks.html#execution-hooks>`_ is invoked.
5. `Layer.__call__`
6. `Layer` artifacts are written to the `Datastore`.

```{eval-rst}
.. rubric:: Scheduler
```

1. The `Layer` is waited on for completion.
2. If the `Layer` fails, the `retry hook <../advanced/hooks.html#retry-hooks>`_ is invoked and the `Layer` retries.
3. The layer's `Record` is written to the `DataStore`.
4. The `Layer` is marked as complete by the scheduler.
5. New runnable layers are identified and scheduled. Return to [3].
