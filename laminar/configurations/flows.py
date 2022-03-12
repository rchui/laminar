import copy
import operator
from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar, Union, overload

from laminar.configurations.datastores import DataStore, Local
from laminar.configurations.executors import Docker, Executor
from laminar.configurations.schedulers import Scheduler
from laminar.settings import current
from laminar.types import unwrap
from laminar.utils import stringify

if TYPE_CHECKING:
    from laminar import Flow, Layer
else:
    Flow = "Flow"
    Layer = "Layer"

T = TypeVar("T", bound=Layer)


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


@dataclass
class Execution:
    #: ID of the flow execution
    id: Optional[str]
    #: Flow being executed
    flow: Flow
    #: True if the flow execution is being retried, else False.
    retry: bool = False

    def __call__(self, id: str) -> "Execution":
        execution = copy.deepcopy(self)
        execution.id = id
        return execution

    def __repr__(self) -> str:
        return stringify(self, type(self).__name__, "id", "retry")

    @property
    def finished(self) -> bool:
        return reduce(operator.and_, [layer.state.finished for layer in self.flow._dependencies.keys()])

    @property
    def running(self) -> bool:
        return (current.execution.id is not None and current.execution.id == self.id) and (
            current.flow.name is not None and current.flow.name == self.flow.name
        )

    @overload
    def layer(self, layer: str, **atributes: Any) -> Layer:
        ...

    @overload
    def layer(self, layer: Type[T], **attributes: Any) -> T:
        ...

    @overload
    def layer(self, layer: T, **attributes: Any) -> T:
        ...

    def layer(self, layer: Union[str, Type[Layer], Layer], **attributes: Any) -> Layer:
        """Get a registered flow layer.

        Usage::

            flow.execution(...).layer("A")
            flow.execution(...).layer(A)
            flow.execution(...).layer(A())
            flow.execution(...).layer(A(), index=0, splits=2)

        Args:
            layer: Layer to get.
            **attributes: Keyword attributes to add to the Layer.

        Returns:
            Layer that is registered to the flow.
        """

        return self.flow.layer(layer, **attributes)

    def resume(self) -> None:
        """Resume a flow execution from where it failed.

        Notes:

            Resuming a flow execution will skip all layers that finished on the previous attempt.

        Usage::

            flow.execution(...).resume()
        """

        self.retry = True
        self.flow.schedule(execution=unwrap(self.id), dependencies=self.flow.dependencies)
