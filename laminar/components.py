"""Core components for build flows."""

import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional, Set, Tuple, Type, Union

from ksuid import KsuidMs

from laminar.configurations import datastores, executors, flows, hooks, layers, schedulers
from laminar.exceptions import FlowError, LayerError
from laminar.settings import current
from laminar.types import LayerType, annotations
from laminar.utils import contexts

logger = logging.getLogger(__name__)

FLOW_RESREVED_KEYWORDS = {"configuration", "execution"}
LAYER_RESERVED_KEYWORDS = {"attempt", "configuration", "flow", "index", "namespace", "splits"}


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

    #: Current layer execution attempt
    attempt: Optional[int] = current.layer.attempt
    #: Layer index in its splits
    index: Optional[int] = current.layer.index
    #: Namespace the Layer is a part of
    namespace: Optional[str] = None
    #: Number of splits in the layer execution
    splits: Optional[int] = current.layer.splits

    def __init__(self, **attributes: Any) -> None:
        for key, value in attributes.items():
            setattr(self, key, value)

    def __init_subclass__(cls, *, namespace: Optional[str] = None) -> None:
        if namespace is not None and not namespace.isalnum():
            raise LayerError(
                "A layer's namespace can only contain alphanumeric characters to ensure filesystem compatability."
                + f" Given namespace '{namespace}'."
            )

        cls.namespace = namespace

    __call__: Callable[..., None]  # type: ignore

    def __call__(self) -> None:  # type: ignore
        ...

    def __repr__(self) -> str:
        attributes = ", ".join(
            f"{key}={repr(value)}"
            for key, value in {attr: getattr(self, attr, None) for attr in ("flow", "index", "splits")}.items()
        )
        return f"{self.name}({attributes})"

    def __deepcopy__(self, memo: Dict[int, Any]) -> "Layer":
        cls = self.__class__
        result: Layer = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    __enter__: Callable[..., bool]  # type: ignore

    def __enter__(self) -> bool:  # type: ignore
        return all(layer.executed for layer in self._dependencies if not isinstance(layer, Parameters))

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
                if not self.executed:
                    message = message + f" Layer {self.name} was not executed."
                raise AttributeError(message) from error

        return self.__dict__[name]

    def __getstate__(self) -> Dict[str, Any]:
        return self.__dict__

    def __hash__(self) -> int:
        return hash(self.name)

    def __setstate__(self, slots: Dict[str, Any]) -> None:
        self.__dict__ = slots

    @property
    def executed(self) -> bool:
        """True if the layer was executed, else False."""

        return self.flow.configuration.datastore.exists(path=datastores.Record.path(layer=self.flow.layer(self)))

    @property
    def name(self) -> str:
        """Name of the layer"""

        if self.namespace is None:
            return type(self).__name__
        return f"{self.namespace}.{type(self).__name__}"

    @property
    def _dependencies(self) -> Tuple["Layer", ...]:
        return annotations(self.flow, self.__call__)

    @property
    def dependencies(self) -> Tuple[str, ...]:
        """Layers this layer depends on."""

        return tuple(layer.name for layer in self._dependencies)

    def _execute(self, *parameters: "Layer") -> None:
        """Execute a layer.

        Args:
            *parameters: Input layers to the layer.
        """

        # Attempt to write any existing layer artifacts before failing
        try:
            self(*parameters)
        finally:
            for artifact, value in vars(self).items():
                if artifact not in LAYER_RESERVED_KEYWORDS:
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


class Flow:
    """Collection of tasks that execute in a specific order.

    Usage::

        from laminar import Flow, Layer

        flow = Flow(name="HelloFlow")
    """

    #: Configurations for the flow
    configuration: flows.Configuration
    #: ID of the flow's current execution
    execution: Optional[str] = current.execution.id

    def __init__(
        self,
        *,
        name: str,
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

        if not name.isalnum():
            raise FlowError(
                "A flow's name can only contain alphanumeric characters to maintain filesystem compatability."
                + f" Given name '{name}'."
            )

        self.name = name

        if isinstance(datastore, datastores.Memory) and not isinstance(executor, executors.Thread):
            raise FlowError("The Memory datastore can only be used with the Thread executor.")

        self.configuration = flows.Configuration(datastore=datastore, executor=executor, scheduler=scheduler)

        self._registry: Dict[str, Layer] = {"Parameters": Parameters(configuration=layers.Configuration())}

    @property
    def _dependencies(self) -> Dict[Layer, Tuple[Layer, ...]]:
        return {
            self.layer(child): tuple(self.layer(parent) for parent in parents)
            for child, parents in self.dependencies.items()
        }

    @property
    def dependencies(self) -> Dict[str, Tuple[str, ...]]:
        """A mapping of each layer and the layers it depends on."""

        return {layer: self.layer(layer).dependencies for layer in self._registry}

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

    def __call__(self, *, execution: Optional[str] = None) -> Optional[str]:
        """Execute the flow or execute a layer in the flow.

        Notes:
            If the execution id and layer name are set, execute a layer.
            Else execute the flow.

        Usage::

            flow = Flow(name="HelloFlow")

            flow()
            flow("execution-id")
        """

        # Execute a layer in the flow.
        if self.execution is not None and self.name == current.flow.name and current.layer.name in self._registry:
            self.execute(execution=self.execution, layer=self.layer(current.layer.name))

        # Schedule execution of the flow.
        elif self.execution is None:
            execution = execution or str(KsuidMs())
            self.schedule(execution=execution, dependencies=self.dependencies)

        return execution

    def __repr__(self) -> str:
        attributes = ", ".join(
            f"{key}={repr(value)}"
            for key, value in {attr: getattr(self, attr, None) for attr in ("execution",)}.items()
        )
        return f"{self.name}({attributes})"

    def execute(self, *, execution: str, layer: Layer) -> None:
        """Execute a single layer of the flow.

        Usage::

            flow = Flow(name="ExecuteFlow")

            @flow.register()
            class A(Layer):
                ...

            flow.execute(execution="test-execution", layer=flow.layer(A, index=0, splits=2))

        Args:
            execution: ID of the execution being run.
            layer: Layer of the flow to execute.
        """

        with contexts.Attributes(layer.flow, execution=execution):

            logger.info("Starting layer '%s'.", layer.name if layer.splits == 1 else f"{layer.name}/{layer.index}")

            # Setup the Layer parameter values
            parameters = layer.configuration.foreach.set(layer=layer, parameters=self._dependencies[layer])

            with hooks.context(layer=layer, annotation=hooks.Annotation.execution):
                layer._execute(*parameters)

            logger.info("Finishing layer '%s'.", layer.name if layer.splits == 1 else f"{layer.name}/{layer.index}")

    def schedule(self, *, execution: str, dependencies: Dict[str, Tuple[str, ...]]) -> None:
        """Schedule layers to run in sequence in the flow.

        Args:
            execution: ID of the execution being run.
            dependencies: Mapping of layers to layers it depends on.
        """

        with contexts.Attributes(self, execution=execution):
            self.configuration.scheduler.loop(flow=self, dependencies=dependencies, finished={"Parameters"})

    def register(
        self,
        container: layers.Container = layers.Container(),
        foreach: layers.ForEach = layers.ForEach(),
        retry: layers.Retry = layers.Retry(),
    ) -> Callable[[LayerType], LayerType]:
        """Add a layer to the flow.

        Usage::

            @flow.register()
            class Task(Layer):
                ...
        """

        def wrapper(Layer: LayerType) -> LayerType:

            layer = Layer(configuration=layers.Configuration(container=container, foreach=foreach, retry=retry))

            if layer.name in self._registry:
                raise FlowError(
                    f"Duplicate layer added to flow '{self.name}'.\n"
                    f"  Given layer '{layer.name}'.\n"
                    f"  Added layers {sorted(self.dependencies)}"
                )

            # First register the layer without the flow attribute
            self._registry[layer.name] = deepcopy(layer)

            return Layer

        return wrapper

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
            Layer that was registered to the flow.
        """

        if isinstance(layer, Layer):
            layer = layer.name
        elif not isinstance(layer, str):
            layer = layer().name

        # Deepcopy so that layer artifacts don't mess with other layer split executions
        layer = deepcopy(self._registry[layer])

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
        with contexts.Attributes(self, execution=execution):

            # Property setup the layer for writing to the datastore
            layer = self.layer(Parameters, index=0, splits=1, attempt=0)

            # Assign artifact values
            for name, value in artifacts.items():
                if name not in LAYER_RESERVED_KEYWORDS:
                    setattr(layer, name, value)

            # Fake an execution to write the artifacts to the datastore.
            layer._execute()

        return execution

    def results(self, execution: str) -> "Flow":
        """Configure the flow to get results for an execution

        Usage::

            from main import flow

            flow.results("21lWJJaHlAYcSE5EtdtH1JmF7fv")

        Args:
            execution: ID of the execution to configure the flow for

        Returns:
            THe flow configured with the execution ID.
        """

        flow = deepcopy(self)
        flow.execution = execution
        return flow
