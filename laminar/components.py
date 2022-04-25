"""Core components for build flows."""

import copy
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Type, TypeVar, Union, overload

from ksuid import KsuidMs

from laminar.configurations import datastores, executors, flows, hooks, layers, schedulers
from laminar.exceptions import ExecutionError, FlowError
from laminar.settings import current
from laminar.types import LayerType, hints, unwrap
from laminar.utils import contexts, stringify

logger = logging.getLogger(__name__)

FLOW_RESERVED_KEYWORDS = {"configuration", "execution"}
LAYER_RESERVED_KEYWORDS = {"attempt", "configuration", "flow", "index", "namespace", "splits", "state"}


@dataclass
class Layer:
    """Task to execute as part of a flow.

    Usage::

        from laminar import Layer

        class Task(Layer):
            ...
    """

    #: Configurations for the Layer
    configuration: layers.Configuration
    #: Flow the Layer is registered to
    flow: "Flow"
    #: Layer state
    state: layers.State

    #: Current layer execution attempt
    attempt: Optional[int] = current.layer.attempt
    #: Layer index in its splits
    index: Optional[int] = current.layer.index
    #: Number of splits in the layer execution
    splits: Optional[int] = current.layer.splits

    def __init__(self, **attributes: Any) -> None:
        for key, value in attributes.items():
            setattr(self, key, value)
        self.state = layers.State(layer=self)

    __call__: Callable[..., None]  # type: ignore

    def __call__(self) -> None:  # type: ignore
        ...

    def __repr__(self) -> str:
        return stringify(self, self.name, "flow", "index", "splits")

    def __deepcopy__(self, memo: Dict[int, Any]) -> "Layer":
        cls = self.__class__
        result: Layer = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        elif isinstance(other, Layer):
            return type(self) is type(other) and self.name == other.name
        else:
            return False

    def __getattr__(self, name: str) -> Any:
        if name not in self.__dict__:
            try:
                self.__dict__[name] = self.flow.configuration.datastore.read_artifact(
                    layer=self, archive=self.configuration.foreach.join(layer=self, name=name)
                )
            except RecursionError as error:
                raise AttributeError(f"Object '{self.name}' has no attribute '{name}'.") from error
            except FileNotFoundError as error:
                message = f"Object '{self.name}' has no attribute '{name}'."
                if not self.state.finished:
                    message = message + f" Layer {self.name} was not finished."
                raise AttributeError(message) from error

        return self.__dict__[name]

    def __getstate__(self) -> Dict[str, Any]:
        return self.__dict__

    def __hash__(self) -> int:
        return hash(self.name)

    def __setstate__(self, slots: Dict[str, Any]) -> None:
        self.__dict__ = slots

    @property
    def artifacts(self) -> Dict[str, Any]:
        """Artifacts assigned to the layer."""

        return {artifact: value for artifact, value in vars(self).items() if artifact not in LAYER_RESERVED_KEYWORDS}

    @property
    def _dependencies(self) -> Tuple["Layer", ...]:
        return hints(self.flow, self.__call__)

    @property
    def dependencies(self) -> Tuple[str, ...]:
        """Layers this layer depends on."""

        return tuple(layer.name for layer in self._dependencies)

    @property
    def hooks(self) -> Dict[str, List[Callable[..., Any]]]:
        """Hooks attached to this layer."""

        _hooks: Dict[str, List[Callable[..., Any]]] = {}
        for entry in list(vars(type(self.flow)).values()) + list(vars(type(self)).values()):
            annotation = hooks.annotation.get(entry)
            if annotation is not None:
                _hooks.setdefault(annotation, []).append(entry)
        return _hooks

    @property
    def name(self) -> str:
        """Name of the Layer"""

        return type(self).__name__

    def _execute(self, *parameters: "Layer") -> None:
        """Execute a layer.

        Args:
            *parameters: Input layers to the layer.
        """

        # Attempt to write any existing layer artifacts before failing
        try:
            self(*parameters)
        finally:
            for artifact, value in self.artifacts.items():
                self.flow.configuration.datastore.write(layer=self, name=artifact, values=[value])

    def shard(self, **artifacts: Iterable[Any]) -> None:
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


class Parameters(Layer):
    """Special Layer for handling Flow parameters."""


T = TypeVar("T", bound=Layer)


class Flow:
    """Collection of tasks that execute in a specific order.

    Usage::

        from laminar import Flow, Layer

        class HelloFlow(Flow):
            ...
    """

    registry: Dict[str, Layer]
    """Layers registered with the flow"""

    def __init__(
        self,
        *,
        datastore: datastores.DataStore = datastores.Local(),
        executor: executors.Executor = executors.Docker(),
        scheduler: schedulers.Scheduler = schedulers.Scheduler(),
    ) -> None:
        """
        Args:
            name (str): Name of the flow. Must be alphanumeric.

        Raises:
            FlowError: If the flow's name is not alphanumeric
        """

        self.name = type(self).__name__
        self.execution = flows.Execution(id=current.execution.id, flow=self)

        if isinstance(datastore, datastores.Memory) and not isinstance(executor, executors.Thread):
            raise FlowError("The Memory datastore can only be used with the Thread executor.")

        self.configuration = flows.Configuration(datastore=datastore, executor=executor, scheduler=scheduler)

    def __init_subclass__(cls) -> None:
        cls.registry = {
            "Parameters": Parameters(configuration=layers.Configuration()),
            **getattr(cls, "registry", {}),
        }

    @property
    def _dependencies(self) -> Dict[Layer, Tuple[Layer, ...]]:
        return {
            self.layer(child): tuple(self.layer(parent) for parent in parents)
            for child, parents in self.dependencies.items()
        }

    @property
    def dependencies(self) -> Dict[str, Tuple[str, ...]]:
        """A mapping of each layer and the layers it depends on."""

        return {layer: self.layer(layer).dependencies for layer in self.registry}

    @property
    def _dependents(self) -> Dict[Layer, Set[Layer]]:
        return {
            self.layer(parent): {self.layer(child) for child in children}
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

    def __call__(self, *, execution: Optional[str] = None, **attributes: Any) -> flows.Execution:
        """Execute the flow or execute a layer in the flow.

        Notes:
            If the execution id and layer name are set, execute a layer.
            Else execute the flow.

        Usage::

            class HelloFlow(Flow):
                ...
            flow = HelloFlow()

            flow()
            flow("execution-id")
        """

        # Execute a layer in the flow.
        if self.execution.id is not None and self.name == current.flow.name and current.layer.name in self.registry:
            execution = self.execution.id
            self.execute(execution=self.execution.id, layer=self.layer(current.layer.name))

        # Schedule execution of the flow.
        elif self.execution.id is None:
            self.execution = flows.Execution(id=execution or str(KsuidMs()), flow=self)
            self.parameters(execution=self.execution.id, **attributes)
            self.schedule(execution=unwrap(self.execution.id), dependencies=self.dependencies)

        return self.execution

    def __repr__(self) -> str:
        return stringify(self, self.name, "execution")

    def execute(self, *, execution: str, layer: Layer) -> None:
        """Execute a single layer of the flow.

        Usage::

            class ExecutionFlow(Flow):
                ...

            @ExecutionFlow.register()
            class A(Layer):
                ...

            flow = ExecutionFlow()
            flow.execute(execution="test-execution", layer=flow.layer(A, index=0, splits=2))

        Args:
            execution: ID of the execution being run.
            layer: Layer of the flow to execute.
        """

        with contexts.Attributes(layer.flow.execution, id=execution):

            logger.info("Starting layer '%s'.", layer.name if layer.splits == 1 else f"{layer.name}/{layer.index}")

            # Setup the Layer parameter values
            parameters = layer.configuration.foreach.set(layer=layer, parameters=self._dependencies[layer])

            with hooks.event.context(layer=layer, annotation=hooks.annotation.execution):
                layer._execute(*parameters)

            logger.info("Finishing layer '%s'.", layer.name if layer.splits == 1 else f"{layer.name}/{layer.index}")

    def schedule(self, *, execution: str, dependencies: Dict[str, Tuple[str, ...]]) -> None:
        """Schedule layers to run in sequence in the flow.

        Args:
            execution: ID of the execution being run.
            dependencies: Mapping of layers to layers it depends on.
        """

        with contexts.Attributes(self.execution, id=execution):
            self.configuration.scheduler.loop(flow=self, dependencies=dependencies, finished={"Parameters"})

    @classmethod
    def register(
        cls,
        container: layers.Container = layers.Container(),
        foreach: layers.ForEach = layers.ForEach(),
        retry: layers.Retry = layers.Retry(),
    ) -> Callable[[LayerType], LayerType]:
        """Add a layer to the flow.

        Usage::

            @Flow.register()
            class Task(Layer):
                ...
        """

        def wrapper(Layer: LayerType) -> LayerType:

            layer = Layer(configuration=layers.Configuration(container=container, foreach=foreach, retry=retry))

            if layer.name in cls.registry:
                raise FlowError(
                    f"Duplicate layer added to flow '{cls.__name__}'.\n"
                    f"  Given layer '{layer.name}'.\n"
                    f"  Added layers {sorted(cls.registry)}"
                )

            # First register the layer without the flow attribute
            cls.registry[layer.name] = copy.deepcopy(layer)

            return Layer

        return wrapper

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

            flow.layer("A")
            flow.layer(A)
            flow.layer(A())
            flow.layer(A(), index=0, splits=2)

        Args:
            layer: Layer to get.
            **attributes: Keyword attributes to add to the Layer.

        Returns:
            Layer that is registered to the flow.
        """

        if isinstance(layer, Layer):
            layer = layer.name
        elif not isinstance(layer, str):
            layer = layer().name

        # Deepcopy so that layer artifacts don't mess with other layer split executions
        layer = copy.deepcopy(self.registry[layer])

        # Inject the flow attribute to link the layer to the flow
        layer.flow = self
        for key, value in attributes.items():
            setattr(layer, key, value)

        return layer

    def parameters(self, *, execution: Optional[str] = None, **artifacts: Any) -> str:
        """Configure parameters for a flow execution

        Usage::

            execution = flow.parameters(foo="bar:)
            flow(execution=execution)

        Args:
            execution: ID of the execution to configure the flow parameters for.
            artifacts: Key/value pairs of parameters to add to the flow.

        Returns:
            ID of the execution the parameters were added to.
        """

        execution = execution or str(KsuidMs())
        with contexts.Attributes(self.execution, id=execution):

            # Property setup the layer for writing to the datastore
            layer = self.layer(Parameters, index=0, splits=1, attempt=0)

            # Assign artifact values
            for name, value in artifacts.items():
                if name in LAYER_RESERVED_KEYWORDS:
                    raise ExecutionError(
                        "A flow parameter is in the list of layer reserved keywords:"
                        f" {sorted(LAYER_RESERVED_KEYWORDS)}. Given {name}."
                    )
                setattr(layer, name, value)

            # Fake an execution to write the artifacts to the datastore.
            self.execute(execution=execution, layer=layer)

            # Record parameter layer execution
            layer.flow.configuration.datastore.write_record(
                layer=layer,
                record=datastores.Record(
                    flow=datastores.Record.FlowRecord(name=layer.flow.name),
                    layer=datastores.Record.LayerRecord(name=layer.name),
                    execution=datastores.Record.ExecutionRecord(splits=unwrap(layer.splits)),
                ),
            )

        return execution
