# from dataclasses import dataclass
import inspect
import logging
from copy import deepcopy
from typing import Any, Callable, Dict, Optional, Sequence, Set, Tuple, Type, TypeVar

from ksuid import Ksuid

from laminar.configurations import datastores, executors, flows, layers
from laminar.configurations.datastores import Accessor
from laminar.exceptions import FlowError
from laminar.settings import current

logger = logging.getLogger(__name__)

LAYER_RESERVED_KEYWORDS = {"configuration", "flow", "index", "splits"}


class Layer:
    """Task to execute as part of a flow.

    Usage::

        from laminar import Layer

        class Task(Layer):
            ...
    """

    configuration: layers.Configuration
    flow: "Flow"
    index: Optional[int] = current.layer.index
    splits: Optional[int] = current.layer.splits

    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def __call__(self) -> None:
        ...

    def __deepcopy__(self, memo: Dict[int, Any]) -> "Layer":
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        elif isinstance(other, Layer):
            return type(self) is type(other) and self.name == other.name
        else:
            return False

    def __getattr__(self, name: str) -> Any:
        # First attempt to get the attribute normally.
        try:
            value = object.__getattribute__(self, name)

        # Fall back to getting a layer artifact.
        except AttributeError:
            indexes = self.configuration.foreach.size(layer=self)

            # The layer has only one index. Get the artifact directly
            if indexes == 1:
                value = self.flow.configuration.datastore.read(layer=self, index=0, name=name)

            # The layer has multiple indexes. Create an accessor for all artifact indexes.
            else:
                value = Accessor(archive=self.configuration.foreach.join(layer=self, name=name), layer=self)

        return value

    def __getstate__(self) -> Dict[str, Any]:
        return self.__dict__

    def __hash__(self) -> int:
        return hash(self.name)

    def __setstate__(self, slots: Dict[str, Any]) -> None:
        self.__dict__ = slots

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    def _dependencies(self) -> Tuple["Layer", ...]:
        return tuple(
            self.flow.get_layer(name=parameter.annotation().name)
            for parameter in inspect.signature(self.__call__).parameters.values()
        )

    @property
    def dependencies(self) -> Tuple[str, ...]:
        return tuple(layer.name for layer in self._dependencies)

    def shard(self, **artifacts: Sequence[Any]) -> None:
        """Store each item of a sequence separately so that they may be loaded individually downstream.

        Notes:
            The artifact that is loaded is of type laminar.configurations.datastores.Accessor.

        Usage::

            class Task(Layer):
                def __call__(self) -> None:
                    self.shard(foo=["a", "b", "c"])

        Args:
            **artifacts: Sequence to break up and store.
        """

        for artifact, sequence in artifacts.items():
            self.flow.configuration.datastore.write(layer=self, name=artifact, values=sequence)


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
        self.configuration = flows.Configuration(datastore=datastore, executor=executor)

        self.dependencies: Dict[str, Tuple[str, ...]] = {}
        self._registry: Dict[str, Layer] = {}

    @property
    def _dependencies(self) -> Dict[Layer, Tuple[Layer, ...]]:
        return {
            self.get_layer(name=child): tuple(self.get_layer(name=parent) for parent in parents)
            for child, parents in self.dependencies.items()
        }

    @property
    def _dependents(self) -> Dict[Layer, Set[Layer]]:
        return {
            self.get_layer(name=parent): {self.get_layer(name=child) for child in children}
            for parent, children in self.dependents.items()
        }

    @property
    def dependents(self) -> Dict[str, Set[str]]:
        """A mapping of each layer and the layers that depend on it."""

        dependents: Dict[str, Set[str]] = {}
        for child, parents in self.dependencies.items():
            for parent in parents:
                dependents.setdefault(parent, set()).add(child)
        return dependents

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
            layer = self.get_layer(name=current.layer.name)
            self.execute(layer=layer)

        # Execute the flow.
        else:
            self.execution = str(Ksuid())
            self.schedule(execution=self.execution, dependencies=self.dependencies)
            self.execution = None

    def execute(self, *, layer: Layer) -> None:
        """Execute a single layer of the flow.

        Args:
            layer (Layer): Layer of the flow to execute.
        """

        parameters = self._dependencies[layer]
        parameters = layer.configuration.foreach.set(layer=layer, parameters=parameters)

        logger.info("Starting layer '%s'.", layer.name)
        layer(*parameters)
        logger.info("Finishing layer '%s'.", layer.name)

        artifacts = vars(layer)
        for artifact, value in artifacts.items():
            if artifact not in LAYER_RESERVED_KEYWORDS:
                self.configuration.datastore.write(layer=layer, name=artifact, values=[value])

    def schedule(self, *, execution: str, dependencies: Dict[str, Tuple[str, ...]]) -> None:
        """Schedule layers to run in sequence in the flow.

        Args:
            execution (str): ID of the execution being run.
            dependencies (Dict[Layer, Tuple[Layer, ...]]): Mapping of layers to layers it depends on.
        """

        def get_pending(*, dependencies: Dict[str, Tuple[str, ...]], finished: Set[str]) -> Set[Layer]:
            return {
                self.get_layer(name=child)
                for child, parents in dependencies.items()
                if child not in finished and set(parents).issubset(finished)
            }

        finished: Set[str] = set()
        pending = get_pending(dependencies=dependencies, finished=finished)

        while pending:
            for layer in pending:

                # Set dynamic layer configuration
                object.__setattr__(layer.configuration, "container", layer.configuration.container.set(layer=layer))

                self.configuration.executor.run(execution=execution, layer=layer)

                finished.add(layer.name)

            pending = get_pending(dependencies=dependencies, finished=finished)

            if not pending and (set(dependencies) - finished):
                raise FlowError(
                    f"A dependency exists for a step that is not registered with the {self.name} flow."
                    f" Finished steps: {sorted(finished)}."
                    f" Remaining dependencies: {dependencies}."
                )

    def layer(
        self, container: layers.Container = layers.Container(), foreach: layers.ForEach = layers.ForEach()
    ) -> Callable[[L], L]:
        """Add a layer to the flow.

        Usage::

            @flow.layer()
            class Task(Layer):
                ...
        """

        def wrapper(Layer: L) -> L:

            layer = Layer(configuration=layers.Configuration(container=container, foreach=foreach))

            if layer.name in self.dependencies:
                raise FlowError(
                    f"Duplicate layer added to flow '{self.name}'.\n"
                    f"  Given layer '{layer.name}'.\n"
                    f"  Added layers {sorted(self.dependencies)}"
                )

            # First register the layer without the flow attribute
            self._registry[layer.name] = deepcopy(layer)

            # Then inject it to get the layer dependencies
            layer.flow = self
            self.dependencies[layer.name] = layer.dependencies

            return Layer

        return wrapper

    def get_layer(self, *, name: str) -> Layer:
        """Get a registered flow layer.

        Args:
            name (str): Name of the layer to get.

        Returns:
            Layer: Layer that was registered to the flow.
        """

        # Deepcopy so that layer artifacts don't mess with other layer split executions
        layer = deepcopy(self._registry[name])

        # Inject the flow attribute to link the layer to the flow
        layer.flow = self
        return layer
