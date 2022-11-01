"""Core components for build flows."""

import copy
import logging
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from functools import reduce
from itertools import chain
from typing import Any, Callable, Dict, Iterable, Optional, Set, Tuple, Type, TypeVar, Union, overload

from ksuid import KsuidMs

from laminar.configurations import datastores, executors, flows, hooks, layers, schedulers
from laminar.exceptions import FlowError
from laminar.settings import current
from laminar.types import hints, unwrap
from laminar.utils import stringify

logger = logging.getLogger(__name__)

FLOW_RESERVED_KEYWORDS = {"configuration", "execution", "registry"}
LAYER_RESERVED_KEYWORDS = {"configuration", "execution", "attempt", "index", "splits"}


@dataclass
class Layer:
    """Task to execute as part of a flow.

    Usage::

        from laminar import Layer

        class Task(Layer): ...
    """

    #: Configurations for the Layer
    configuration: layers.Configuration
    #: Execution the layer is being run in
    execution: "Execution"

    #: Current layer execution attempt
    attempt: Optional[int] = current.layer.attempt
    #: Layer index in its splits
    index: Optional[int] = current.layer.index
    #: Number of splits in the layer execution
    splits: Optional[int] = current.layer.splits

    def __init__(self, **attributes: Any) -> None:
        for key, value in attributes.items():
            setattr(self, key, value)

    __call__: Callable[..., None]  # type: ignore

    def __call__(self) -> None:  # type: ignore
        ...

    def __repr__(self) -> str:
        return stringify(self, self.name, "execution", "index", "splits")

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
            # The key is a reserved keyword. We expect these to all be here.
            if name in LAYER_RESERVED_KEYWORDS:
                raise AttributeError(f"Object '{self.name}' has no attribute '{name}'.")

            # The key is likely an artifact.
            try:
                self.__dict__[name] = self.execution.flow.configuration.datastore.read_artifact(
                    layer=self, archive=self.configuration.foreach.join(layer=self, name=name)
                )
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

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name < other
        elif isinstance(other, Layer):
            return self.name < other.name
        else:
            raise TypeError(f"Type '{type(self).__name__}' and type '{type(other).__name__}' are incomparable.")

    def __setstate__(self, slots: Dict[str, Any]) -> None:
        self.__dict__ = slots

    @property
    def artifacts(self) -> Dict[str, Any]:
        """Artifacts assigned to the layer."""

        return {artifact: value for artifact, value in vars(self).items() if artifact not in LAYER_RESERVED_KEYWORDS}

    @property
    def _hooks(self) -> Set[Callable[..., Any]]:
        return {
            hook
            for hook in chain(vars(type(self.execution.flow)).values(), vars(type(self)).values())
            if hooks.annotation.get(hook) is not None
        }

    @property
    def _parameters(self) -> Dict[str, Tuple["Layer", ...]]:
        return {
            self.__call__.__name__: hints(self.execution, self.__call__),
            **{hook.__name__: hints(self.execution, hook) for hook in self._hooks},
        }

    @property
    def _dependencies(self) -> Set["Layer"]:
        return set(chain.from_iterable(self._parameters.values()))

    @property
    def dependencies(self) -> Set[str]:
        """Layers this layer depends on."""

        return {layer.name for layer in self._dependencies}

    @property
    def hooks(self) -> Dict[str, Set[Callable[..., Any]]]:
        """Hooks attached to this layer collated by annotation."""

        _hooks: Dict[str, Set[Callable[..., Any]]] = defaultdict(set)
        for hook in self._hooks:
            _hooks[unwrap(hooks.annotation.get(hook))].add(hook)
        return _hooks

    @property
    def name(self) -> str:
        """Name of the Layer"""

        return type(self).__name__

    @property
    def state(self) -> layers.State:
        """State of the Layer"""

        return layers.State(layer=self)

    def execute(self, *parameters: "Layer") -> None:
        """Execute a layer.

        Args:
            *parameters: Input layers to the layer.
        """

        # Attempt to write any existing layer artifacts before failing
        try:
            with self.configuration.catch:
                self(*parameters)
        finally:
            for artifact, value in self.artifacts.items():
                self.execution.flow.configuration.datastore.write(layer=self, name=artifact, values=[value])

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
            self.execution.flow.configuration.datastore.write(layer=self, name=artifact, values=sequence)


class Parameters(Layer):
    """Special Layer for handling Flow parameters."""


LayerT = TypeVar("LayerT", bound=Layer)


@dataclass
class Execution:
    #: ID of the flow execution
    id: Optional[str]
    #: Flow being executed
    flow: "Flow"
    #: True if the flow execution is being retried, else False.
    retry: bool = False

    def __call__(self, id: str) -> "Execution":
        execution = Execution(id=id, flow=self.flow, retry=self.retry)
        self.flow.execution = execution
        return execution

    def __repr__(self) -> str:
        return stringify(self, type(self).__name__, "id", "retry", "flow")

    @property
    def finished(self) -> bool:
        """Flow execution is finished."""

        return reduce(operator.and_, [layer.state.finished for layer in self.flow._dependencies.keys()])

    @property
    def running(self) -> bool:
        """Flow execution is currently running."""

        execution_id, flow_name = current.execution.id, current.flow.name
        return (execution_id is not None and execution_id == self.id) and (
            flow_name is not None and flow_name == self.flow.name
        )

    def execute(self, *, layer: Layer) -> "Execution":
        """Execute a single layer of the flow.

        Usage::

            class ExecutionFlow(Flow): ...

            @ExecutionFlow.register
            class A(Layer): ...

            flow = ExecutionFlow()
            flow.execution(...).execute(layer=flow.layer(A, index=0, splits=2))

        Args:
            layer: Layer of the flow to execute.
        """

        logger.info("Starting layer '%s'.", layer.name if layer.splits == 1 else f"{layer.name}/{layer.index}")

        # Setup the Layer parameter values
        parameters = layer.configuration.foreach.set(layer=layer, parameters=layer._parameters["__call__"])

        with hooks.event.context(layer=layer, annotation=hooks.annotation.execution):
            layer.execute(*parameters)

        logger.info("Finishing layer '%s'.", layer.name if layer.splits == 1 else f"{layer.name}/{layer.index}")

        return self

    def next(self, *, flow: "Flow", linker: Callable[["Execution"], "Parameters"]) -> "Execution":
        """Chain multiple flow executions together.

        Usage::

            class Flow1(Flow): ...
            class Flow2(Flow): ...

            @Flow1.register
            class A(Layer):
                foo: str

            flow1 = Flow1()

            flow_1().next(
                flow=Flow2(),
                linker=lambda execution: Parameters(foo=execution.layer(A).foo)
            )

        Args:
            flow: Flow to execute next.
            linker: Function for passing parameters to the next flow.
        """

        artifacts = (
            linker(self).artifacts
            if all(variable is None for variable in (current.execution.id, current.flow.name, current.layer.name))
            else {}
        )
        return flow(execution=self.id, **artifacts)

    @overload
    def layer(self, layer: str, **atributes: Any) -> Layer:
        ...

    @overload
    def layer(self, layer: Type[LayerT], **attributes: Any) -> LayerT:
        ...

    @overload
    def layer(self, layer: LayerT, **attributes: Any) -> LayerT:
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

        if isinstance(layer, Layer):
            layer = layer.name
        elif not isinstance(layer, str):
            layer = layer().name

        # Deepcopy so that layer artifacts don't mess with other layer split executions
        layer = copy.deepcopy(self.flow.registry[layer])

        # Inject the execution attribute to link the layer to an execution
        layer.execution = self
        for key, value in attributes.items():
            setattr(layer, key, value)

        return layer

    def parameters(self, **artifacts: Any) -> "Execution":
        """Configure parameters for a flow execution

        Usage::

            flow.execution(...).parameters(foo="bar")

        Args:
            artifacts: Key/value pairs of parameters to add to the flow.

        Returns:
            ID of the execution the parameters were added to.
        """

        # Properly setup the layer for writing to the datastore
        layer = self.layer(Parameters, index=0, splits=1, attempt=0, **artifacts)

        # Fake an execution to write the artifacts to the datastore.
        execution = self.execute(layer=layer)

        # Record parameter layer execution
        layer.execution.flow.configuration.datastore.write_record(
            layer=layer,
            record=datastores.Record(
                flow=datastores.Record.FlowRecord(name=layer.execution.flow.name),
                layer=datastores.Record.LayerRecord(name=layer.name),
                execution=datastores.Record.ExecutionRecord(splits=unwrap(layer.splits)),
            ),
        )

        return execution

    def resume(self) -> "Execution":
        """Resume a flow execution from where it failed.

        Notes:

            Resuming a flow execution will skip all layers that finished on the previous attempt.

        Usage::

            flow.execution(...).resume()
        """

        self.retry = True
        return self.schedule(dependencies=self.flow.dependencies)

    def schedule(self, *, dependencies: Dict[str, Set[str]]) -> "Execution":
        """Schedule layers to run in sequence in the flow execution.

        Args:
            dependencies: Mapping of layers to layers it depends on.
        """

        self.flow.configuration.scheduler.loop(  # type: ignore
            execution=self, dependencies=dependencies, finished={Parameters().name}
        )

        return self


@dataclass
class Flow:
    """Collection of tasks that execute in a specific order.

    Usage::

        from laminar import Flow, Layer

        class HelloFlow(Flow): ...
    """

    #: Execution of the flow
    execution: Execution
    #: Flow configuration
    configuration: flows.Configuration
    #: Layers registered with the flow
    registry: Dict[str, Layer] = field(default_factory=dict)

    def __init__(
        self,
        *,
        datastore: datastores.DataStore = datastores.Local(),
        executor: executors.Executor = executors.Docker(),
        scheduler: schedulers.Scheduler = schedulers.Scheduler(),
    ) -> None:
        """
        Args:
            datastore: Datastore to execute the flow with. Optional; Defaults to datastores.Local().
            executor: Executor to run layers with. Optional; Defaults to executors.Docker().
            scheduler: Scheduler to manage the flow with. Optional; Defaults to schedulers.Scheduler().

        Raises:
            FlowError: If the flow is used to configure the Memory datastore without a Thread executor.
        """

        self.execution = Execution(id=current.execution.id, flow=self)
        self.configuration = flows.Configuration(datastore=datastore, executor=executor, scheduler=scheduler)

    def __init_subclass__(cls) -> None:
        flow: Type[Flow]
        layer: Layer

        # Register all subflow layers with this layer
        cls.registry = {Parameters().name: Parameters(configuration=layers.Configuration())}
        for flow in cls.__bases__:
            for name, layer in getattr(flow, "registry", {}).items():
                if name != Parameters().name:
                    callback = cls.register(
                        container=layer.configuration.container,
                        foreach=layer.configuration.foreach,
                        retry=layer.configuration.retry,
                    )
                    callback(layer.__class__)

    @property
    def _dependencies(self) -> Dict[Layer, Set[Layer]]:
        return {
            self.execution.layer(child): {self.execution.layer(parent) for parent in parents}
            for child, parents in self.dependencies.items()
        }

    @property
    def dependencies(self) -> Dict[str, Set[str]]:
        """A mapping of each layer and the layers it depends on."""

        return {layer: self.execution.layer(layer).dependencies for layer in self.registry}

    @property
    def _dependents(self) -> Dict[Layer, Set[Layer]]:
        return {
            self.execution.layer(parent): {self.execution.layer(child) for child in children}
            for parent, children in self.dependents.items()
        }

    @property
    def dependents(self) -> Dict[str, Set[str]]:
        """A mapping of each layer and the layers that depend on it."""

        dependents: Dict[str, Set[str]] = defaultdict(set)
        for child, parents in self.dependencies.items():
            for parent in parents:
                dependents[parent].add(child)
        return dependents

    @property
    def name(self) -> str:
        return type(self).__name__

    def __bool__(self) -> bool:
        if self.execution.id is None:
            return True

        if self.execution.id is not None and self.name == current.flow.name and current.layer.name in self.registry:
            self.execution.execute(layer=self.execution.layer(current.layer.name))

        return False

    def __call__(self, *, execution: Optional[str] = None, **parameters: Any) -> Execution:
        """Execute the flow or execute a layer in the flow.

        Notes:
            If the execution id and layer name are set, execute a layer.
            Else execute the flow.

        Usage::

            class HelloFlow(Flow): ...
            flow = HelloFlow()

            flow()
            flow("execution-id")
        """

        if self:
            self.execution = self.execution(execution or str(KsuidMs()))
            self.execution.parameters(**parameters).schedule(dependencies=self.dependencies)

        return self.execution

    def __repr__(self) -> str:
        return stringify(self, self.name, empty=True)

    @overload
    @classmethod
    def register(cls, layer: Type[LayerT]) -> Type[LayerT]:
        ...

    @overload
    @classmethod
    def register(
        cls,
        *,
        catch: layers.Catch = layers.Catch(),
        container: layers.Container = layers.Container(),
        foreach: layers.ForEach = layers.ForEach(),
        retry: layers.Retry = layers.Retry(),
    ) -> Callable[[Type[LayerT]], Type[LayerT]]:
        ...

    @classmethod
    def register(cls, *args: Any, **kwargs: Any) -> Any:
        """Add a layer to the flow.

        Usage::

            @Flow.register
            class Task(Layer): ...

            @Flow.register(...)
            class Task(Layer): ...
        """

        def add_layer(flow: Type[Flow], layer: Layer) -> None:
            """Add a Layer to the Flow registry."""

            if layer.name in flow.registry:
                raise FlowError(
                    f"Duplicate layer added to flow '{flow.__name__}'.\n"
                    f"  Given layer '{layer.name}'.\n"
                    f"  Added layers {sorted(flow.registry)}"
                )

            flow.registry[layer.name] = copy.deepcopy(layer)

        # 1st form: Register a layer with user-defined configurations
        # @Flow.register
        if args:
            LayerDef: Type[Layer] = args[0]
            layer = LayerDef(configuration=layers.Configuration())

            add_layer(cls, layer)

            return LayerDef

        # 2nd form: Register a layer with user-defined configurations
        # @Flow.register
        else:

            def wrapper(Layer: Type[LayerT]) -> Type[LayerT]:
                layer = Layer(
                    configuration=layers.Configuration(
                        catch=kwargs.get("catch", layers.Catch()),
                        container=kwargs.get("container", layers.Container()),
                        foreach=kwargs.get("foreach", layers.ForEach()),
                        retry=kwargs.get("retry", layers.Retry()),
                    )
                )

                add_layer(cls, layer)

                return Layer

            return wrapper
