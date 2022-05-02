# Ser(De)

`cloudpickle` is used as the default serialization format for reading and writing artifacts to the `laminar` datastore. However, `cloudpickle` has many downsides that make it undesirable for serializing and deserializing data including but not limited to:

1. Insecure and a vector for RCE
1. Slow
1. Memory intensive
1. Issues with forwards and backwards incompatability

`laminar` uses cloudpickle because it has great support for a wide variety of Python types and is an effective serialization format for inter-process communication but it may not be what you want.

## Protocols

Users can define custom serialization and deserializations by subclassing `serde.Protocol` and registering it with a `Datastore`. This allows complete control and customization over how a type of data is managed by the `Datastore`.

The minimal number of methods that must be overriden are:

- `Protocol.dumps`
- `Protocol.loads`

Consider the following contrived example:

```python
from typing import Any, List

from laminar import Flow, Layer
from laminar.configurations import datastores, serde

datastore = datastores.Local()

class SerdeFlow(Flow):
    ...

@datastore.protocol(list)
class ListProtcol(serde.Protocol):
    def load(self, file: BinaryIO) -> List[Any]:
        return eval(file.read().decode())

    def loads(self, stream: bytes) ->  List[Any]:
        return eval(stream.decode())

    def dump(self, value: List[Any], file: BinaryIO) -> None:
        file.write(value.__repr__().encode())

    def dumps(self, value: List[Any]) -> bytes:
        return value.__repr__().encode()

flow = SerdeFlow(datastore=datastore)
```

Here we define a `Protocol` to convert lists into byte strings and those are written to and read from the datastore. A `Protocol` can be registered to any vaild Python type and will intercept **exact type matches**.

```{note}
The way that a `Protocol` knows what type is by performing a lookup with the output of `serde.dtype()`. This has some immediately obvious implications:

1. Protocols will not correctly intercept subclasses.
1. Protocol registration can overwrite each other if the registered type name is the same.
```

## Multiple Types

Here is an example for serializing JSON:

```python
import json
from typing import Any, Dict, Union

from laminar import Flow, Layer
from laminar.configurations import datastores, serde

datastore = datastores.Local()

class SerdeFlow(Flow):
    ...

@datastore.protocol(dict, list)
class JsonProtocol(serde.Protocol):
    def load(self, file: BinaryIO) -> Union[Dict[str, Any], List[Any]]:
        return json.load(file)

    def dumps(self, value: Union[Dict[str, Any], List[Any]]) -> bytes:
        return json.dumps(value).encode()

flow = SerdeFlow(datastore=datastore)
```

The `Datastore` registers both `list` and `dict` to the `JsonProtocol` which handles serializing and deserializing them to and from the `Datastore` as JSON.

## Beyond the Datastore

In addition to serde protocols instructing datastores how to serialize and deserialize data, they can also instruct the `Datastore` how to read and write data by overriding `Protocol.read` and `Protocol.write`.

```python
from typing import Any, List

from laminar import Flow, Layer
from laminar.configurations import datastores, serde

cache: Dict[str, List[Any]] = {}
datastore = datastores.Local()

class SerdeFlow(Flow):
    ...

@datastore.protocol(list)
class ListProtcol(serde.Protocol):
    def read(uri: str) -> List[Any]:
        return cache[uri]

    def write(value: List[Any], uri: str) -> None:
        cache[uri] = value

flow = SerdeFlow(datastore=datastore)
```
