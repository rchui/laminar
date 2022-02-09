import copy
import operator
from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, Any, Optional, Type, Union

from laminar.configurations.datastores import DataStore, Local
from laminar.configurations.executors import Docker, Executor
from laminar.configurations.schedulers import Scheduler
from laminar.settings import current

if TYPE_CHECKING:
    from laminar import Flow, Layer
    from laminar.components import Parameters
else:
    Flow = "Flow"
    Layer = "Layer"
    Parameters = "Parameters"


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
    id: Optional[str]
    flow: Flow

    def __call__(self, id: str) -> "Execution":
        execution = copy.deepcopy(self)
        execution.id = id
        return execution

    def __repr__(self) -> str:
        return f"Execution(id={self.id}, flow={self.flow.name})"

    @property
    def finished(self) -> bool:
        return reduce(
            operator.and_,
            [layer.state.finished for layer in self.flow._dependencies.keys() if not isinstance(layer, Parameters)],
        )

    @property
    def running(self) -> bool:
        return (current.execution.id is not None and current.execution.id == self.id) and (
            current.flow.name is not None and current.flow.name == self.flow.name
        )

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
