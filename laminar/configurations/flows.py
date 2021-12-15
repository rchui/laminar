from dataclasses import dataclass

from laminar.configurations.datastores import DataStore, Local
from laminar.configurations.executors import Docker, Executor
from laminar.configurations.schedulers import Active, Scheduler


@dataclass(frozen=True)
class Configuration:
    datastore: DataStore = Local()
    executor: Executor = Docker()
    scheduler: Scheduler = Active()
