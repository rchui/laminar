# Datastores

A `Flow` supports multiple backend data stores which configure where data is stored for the workflow. Layers in the `Flow` will read from and write to the data store to pass artifacts between layers.

## Local

By default, flows are configured to use the `Local` datastore which writes `Flow` artifacts to a location on local disk.

```python
from laminar import Flow
from laminar.configurations import datastores

flow = Flow("LocalFlow", datastore=datastores.Local())
```

## Memory

The `Memory` datastore writes artifacts to an in memory key/value store. This very useful for testing.

```python
from laminar import Flow
from laminar.configurations import datastores

flow = Flow("MemoryFlow", datastore=datastores.Memory())
```

```{warning}
Can only be used with the `Thread` executor because only the main process can write to the `Memory` datastore.
```

## AWS.S3

```{warning}
`AWS.S3` is experimental.
```

The `AWS.S3` datastore writes artifacts to the AWS S3 object storage service.

```python
from laminar import Flow
from laminar.configurations import datastores

flow = Flow("S3Flow", datastore=datastores.AWS.S3())
```
