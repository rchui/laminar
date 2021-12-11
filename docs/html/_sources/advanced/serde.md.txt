# Ser(De)

`cloudpickle` is used as the default serialization format for reading and writing artifacts to the `laminar` datastore. However, `cloudpickle` has many downsides that make it undesirable for serializing and deserializing data including but not limited to:

1. Insecure and a vector for RCE
1. Slow
1. Memory intensive
1. Issues with forwards and backwards incompatability

`laminar` uses cloudpickle because it has great support for a wide variety of Python types and is an effective serialization format for inter-process communication but it may not be what you want.

## Protocols

Users can define custom serialization and deserializations by subclassing `serde.Protocol` and registering it with a `Datastore`. This allows complete control and customizaiton over any type of data that needs to be stored.

Consider the following contrived example:

```python
from typing import Any, List

from laminar import Flow, Layer
from laminar.configurations import datastores, serde

datastore = datastores.Local()

@datastore.protocol(list)
class ListProtcol(serde.Protocol[List[Any]]):
    def load(self, file: BinaryIO) -> List[Any]:
        return eval(file.read().decode())

    def loads(self, stream: bytes) ->  List[Any]:
        return eval(stream.decode())

    def dump(self, value: List[Any], file: BinaryIO) -> None:
        file.write(value.__repr__().encode())

    def dumps(self, value: List[Any]) -> bytes:
        return value.__repr__().encode()

flow = Flow("SerdeFlow", datastore=datastore)
```

Here we define a `Protocol` to convert lists into byte strings and those are written to and read from the datastore. A `Protocol` can be registered to any vaild Python type and will intercept **exact type matches**.

```{note}
The way that a `Protocol` knows what type is by performing a lookup with `type(value).__name__` in `Datastore.protocols`. This has some immediately obvious implications:

1. Protocols will not correctly intercept subclasses.
1. Protocol registration can overwrite each other if the registered type name is the same.
```

## Multiple Types

Here is a more complex example for serializing JSON:

```python
import json
from typing import Any, Dict, Union

from laminar import Flow, Layer
from laminar.configurations import datastores, serde

datastore = datastores.Local()

@datastore.protocol(dict)
@datastore.protocol(list)
class JsonProtocol(serde.Protocol[Union[Dict[str, Any], List[Any]]]):
    def load(self, file: BinaryIO) -> Union[Dict[str, Any], List[Any]]:
        return json.load(file)

    def loads(self, stream: bytes) ->  Union[Dict[str, Any], List[Any]]:
        return json.loads(stream.decode())

    def dump(self, value: Union[Dict[str, Any], List[Any]], file: BinaryIO) -> None:
        json.dump(value, file)

    def dumps(self, value: Union[Dict[str, Any], List[Any]]) -> bytes:
        return json.dumps(value)

flow = Flow("SerdeFlow", datastore=datastore)
```

The `Datastore` registers both `list` and `dict` to the `JsonProtocol` which handles serializing and deserializing them to and from the `Datastore` as JSON.

## Beyond the Datastore

Because a `Protocol` controls how artifacts are serialized and deserialized to files, the `Protocol` can even choose not to write to the `Datastore`. The incoming `file` parameter can be totally ignored. Doing so will overwrite how `Datastore` reads and writes this type.

```python
import boto3

from laminar import Flow, Layer
from laminar.configurations import datastores, serde

datastore = datastores.Local()

@datastore.protocol(dict)
class ListProtcol(serde.Protocol[List[Any]]):
    dynamodb = boto3.resource('dynamodb')

    def load(self, file: BinaryIO) -> List[Any]:
        return dynamodb.Table(...).get_item(...)

    def loads(self, stream: bytes) ->  List[Any]:
        return eval(stream)

    def dump(self, value: List[Any], file: BinaryIO) -> None:
        dynamodb.Table(...).put_item(value)

    def dumps(self, value: List[Any]) -> bytes:
        return str(value)

flow = Flow("SerdeFlow", datastore=datastore)
```
