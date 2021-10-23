# from dataclasses import dataclass
import inspect
import logging
from typing import Any, Dict, Iterable, Optional, Set, Tuple, Type, TypeVar

from ksuid import Ksuid

from laminar.configurations import datastores, executors, layers
from laminar.exceptions import FlowError
from laminar.settings import current

logger = logging.getLogger(__name__)

LAYER_RESERVED_KEYWORDS = {"flow", "metrics"}


class Layer:
    """Task to execute as part of a flow.

    Usage::

        from laminar import Layer

        class Task(Layer):
            ...
    """

    container: layers.Container
    flow: "Flow"
    index: Optional[int] = current.layer.index

    def __init_subclass__(cls, container: layers.Container = layers.Container()) -> None:
        cls.container = container

    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def __call__(self) -> None:
        ...

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        elif isinstance(other, Layer):
            return type(self) is type(other) and self.name == other.name
        else:
            return False

    def __getattr__(self, name: str) -> Any:
        try:
            value = object.__getattribute__(self, name)
        except AttributeError:
            value = self.flow.datastore.read(self, name)
            if isinstance(value, datastores.Accessor):
                setattr(self, name, value)

        return value

    def __hash__(self) -> int:
        return hash(self.name)

    @property
    def name(self) -> str:
        return type(self).__name__

    def fork(self, **artifacts: Iterable[Any]) -> None:
        """Store each item of a sequence separately so that they may be loaded individually downstream.

        Notes:
            The artifact that is loaded is of type laminar.configurations.datastores.Accessor.

        Usage::

            class Task(Layer):
                def __call__(self) -> None:
                    self.fork(foo=["a", "b", "c"])

        Args:
            **artifacts: Iterable to break up and store.
        """

        for artifact, sequence in artifacts.items():
            self.flow.datastore.write(self, artifact, sequence)


L = TypeVar("L", bound=Type[Layer])


class Flow:
    """Collection of tasks that execute in a specific order.

    Usage::

        from laminar import Flow, Layer

        flow = Flow(name="HelloFlow")
    """

    execution: Optional[str] = current.execution.id

    def __init__(
        self,
        *,
        name: str,
        datastore: datastores.DataStore = datastores.Local(),
        executor: executors.Executor = executors.Docker(),
    ) -> None:
        """
        Args:
            name (str): Name of the flow. Must be alphanumeric.

        Raises:
            FlowError: If the flow's name is not alphanumeric
        """

        if not name.isalnum():
            raise FlowError(f"A flow's name can only contain alphanumeric characters. Given name '{name}'.")

        self.name = name
        self.datastore = datastore
        self.executor = executor

        self._dependencies: Dict[Layer, Tuple[Layer, ...]] = {}
        self._mapping: Dict[str, Layer] = {}

    @property
    def dependencies(self) -> Dict[str, Tuple[str, ...]]:
        return {child.name: tuple(parent.name for parent in parents) for child, parents in self._dependencies.items()}

    def __call__(self) -> None:
        """Execute the flow or execute a layer in the flow.

        Notes:
            If the execution id and layer name are set, execute a layer.
            Else execute the flow.

        Usage::

            flow = Flow(name = "HelloFlow")
            flow()
        """

        # Execute a layer in the flow.
        if self.execution and current.layer.name:
            layer = self._mapping[current.layer.name]
            self.execute(layer)

        # Execute the flow.
        else:
            self.schedule(str(Ksuid()), self._dependencies)

    def execute(self, layer: Layer) -> None:
        parameters = self._dependencies[layer]

        logger.info("Starting layer '%s'.", layer.name)
        layer(*parameters)
        logger.info("Finishing layer '%s'.", layer.name)

        artifacts = vars(layer)
        for artifact, value in artifacts.items():
            if artifact not in LAYER_RESERVED_KEYWORDS:
                self.datastore.write(layer, artifact, [value])

    def schedule(self, execution: str, dependencies: Dict[Layer, Tuple[Layer, ...]]) -> None:
        def get_pending(dependencies: Dict[Layer, Tuple[Layer, ...]], finished: Set[Layer]) -> Set[Layer]:
            return {
                child
                for child, parents in dependencies.items()
                if child not in finished and set(parents).issubset(finished)
            }

        finished: Set[Layer] = set()
        pending = get_pending(dependencies, finished)

        while pending:
            for layer in pending:

                self.executor.run(execution, layer)

                finished.add(layer)

            pending = get_pending(dependencies, finished)

            if not pending and (set(dependencies) - finished):
                raise FlowError(
                    f"A dependency exists for a step that is not registered with the {self.name} flow."
                    f" Finished steps: {sorted(finished)}."
                    f" Remaining dependencies: {dependencies}."
                )

    def layer(self, Layer: L) -> L:
        """Add a layer to the flow.

        Usage::

            @flow.layer
            class Task(Layer):
                ...
        """

        layer = Layer(flow=self)

        if layer in self._dependencies:
            raise FlowError(f"Duplicate layer added to flow '{self.name}'. Given layer '{layer.name}'.")

        self._dependencies[layer] = tuple(
            parameter.annotation(flow=self) for parameter in inspect.signature(layer.__call__).parameters.values()
        )
        self._mapping[layer.name] = layer

        return Layer
