from dataclasses import dataclass

from laminar.configurations.datastores import DataStore, Local
from laminar.configurations.executors import Docker, Executor
from laminar.configurations.schedulers import Scheduler


@dataclass(frozen=True)
class Configuration:
    """Flow configurations.

    Usage::

        class A(Layer):
            def __call__(self) -> None:
                self.flow.configuration.datastore
                self.flow.configuration.executor
                self.flow.configuration.scheduler
    """

    #: Flow datastore configuration
    datastore: DataStore = Local()
    #: Flow executor configuration
    executor: Executor = Docker()
    #: Flow scheduler configuration
    scheduler: Scheduler = Scheduler()
