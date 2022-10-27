"""Configurations for laminar flows."""

import logging
from dataclasses import dataclass, field

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
    datastore: datastores.DataStore = field(default_factory=datastores.Local)
    #: Flow executor configuration
    executor: executors.Executor = field(default_factory=executors.Docker)
    #: Flow scheduler configuration
    scheduler: schedulers.Scheduler = field(default_factory=schedulers.Scheduler)

    def __post_init__(self) -> None:
        if isinstance(self.datastore, datastores.Memory) and not isinstance(self.executor, executors.Thread):
            raise FlowError("The Memory datastore can only be used with the Thread executor.")
