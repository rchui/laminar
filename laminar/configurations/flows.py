from dataclasses import asdict, dataclass
from typing import Any, Dict, Union

from dacite.core import from_dict

from laminar.configurations.datastores import DataStore, Local
from laminar.configurations.executors import Docker, Executor


@dataclass(frozen=True)
class Configuration:
    datastore: DataStore = Local()
    executor: Executor = Docker()

    def __or__(self, other: Union[DataStore, Executor]) -> "Configuration":
        new: Dict[str, Any]

        if isinstance(other, DataStore):
            new = {"datastore": other}
        elif isinstance(other, Executor):
            new = {"executor": other}
        else:
            raise NotImplementedError

        return from_dict(Configuration, {**asdict(self), **new})
