"""Configurations for laminar flows."""

import logging
from dataclasses import dataclass

from laminar.configurations import datastores, executors, schedulers
from laminar.exceptions import FlowError

logger = logging.getLogger(__name__)


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
    datastore: datastores.DataStore = datastores.Local()
    #: Flow executor configuration
    executor: executors.Executor = executors.Docker()
    #: Flow scheduler configuration
    scheduler: schedulers.Scheduler = schedulers.Scheduler()

    def __post_init__(self) -> None:
        if isinstance(self.datastore, datastores.Memory) and not isinstance(self.executor, executors.Thread):
            raise FlowError("The Memory datastore can only be used with the Thread executor.")
