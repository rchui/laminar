from dataclasses import dataclass

from laminar.configurations.datastores import DataStore, Local
from laminar.configurations.executors import Docker, Executor


@dataclass(frozen=True)
class Configuration:
    datastore: DataStore = Local()
    executor: Executor = Docker()
