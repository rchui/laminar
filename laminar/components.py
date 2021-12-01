import asyncio
import logging
from copy import deepcopy
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Set, Tuple, Type, Union

from ksuid import KsuidMs

from laminar.configurations import datastores, executors, flows, hooks, layers
from laminar.exceptions import FlowError, LayerError
from laminar.settings import current
from laminar.types import LayerType, annotations
from laminar.utils import contexts

logger = logging.getLogger(__name__)

FLOW_RESREVED_KEYWORDS = {"execution"}
LAYER_RESERVED_KEYWORDS = {"configuration", "flow", "index", "namespace", "splits"}


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
    namespace: Optional[str] = None
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

    __call__: Callable[..., None]

    def __call__(self) -> None:  # type: ignore
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
        return self.flow.configuration.datastore.read_artifact(
            layer=self, archive=self.configuration.foreach.join(layer=self, name=name)
        )

    def __getstate__(self) -> Dict[str, Any]:
        return self.__dict__

    def __hash__(self) -> int:
        return hash(self.name)

    def __setstate__(self, slots: Dict[str, Any]) -> None:
        self.__dict__ = slots

    @property
    def name(self) -> str:
        if self.namespace is None:
            return type(self).__name__
        return f"{self.namespace}.{type(self).__name__}"

    @property
    def _dependencies(self) -> Tuple["Layer", ...]:
        return tuple(self.flow.layer(annotation) for annotation in annotations(self.__call__))

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
            raise FlowError(
                "A flow's name can only contain alphanumeric characters to maintain filesystem compatability."
                + f" Given name '{name}'."
            )

        self.name = name

        if isinstance(datastore, datastores.Memory) and not isinstance(executor, executors.Thread):
            raise FlowError("The Memory datastore can only be used with the Thread executor.")

        self.configuration = flows.Configuration(datastore=datastore, executor=executor)

        self._registry: Dict[str, Layer] = {}

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

    def __call__(self) -> None:
        """Execute the flow or execute a layer in the flow.

        Notes:
            If the execution id and layer name are set, execute a layer.
            Else execute the flow.

        Usage::

            flow = Flow(name="HelloFlow")
            flow()
        """

        # Execute a layer in the flow.
        if self.execution is not None and self.name == current.flow.name and current.layer.name is not None:
            self.execute(execution=self.execution, layer=self.layer(current.layer.name))

        # Execute the flow.
        elif self.execution is None:
            self.schedule(execution=str(KsuidMs()), dependencies=self.dependencies)

    def execute(self, *, execution: str, layer: Layer) -> None:
        """Execute a single layer of the flow.

        Usage::

            flow = Flow(name="ExecuteFlow")

            @flow.register()
            class A(Layer):
                ...

            flow.execute(execution="test-execution", layer=flow.layer(A, index=0, splits=2))

        Args:
            execution (str): ID of the execution being run.
            layer (Layer): Layer of the flow to execute.
        """

        with contexts.Attributes(layer.flow, execution=execution):

            logger.info("Starting layer '%s'.", layer.name)

            # Setup the Layer parameter values
            parameters = layer.configuration.foreach.set(layer=layer, parameters=self._dependencies[layer])

            with hooks.context(layer=layer, annotation=hooks.annotation.execution):
                layer(*parameters)

            # Write the layer artifacts back to the flow datastore.
            artifacts = vars(layer)
            for artifact, value in artifacts.items():
                if artifact not in LAYER_RESERVED_KEYWORDS:
                    self.configuration.datastore.write(layer=layer, name=artifact, values=[value])

            logger.info("Finishing layer '%s'.", layer.name)

    @contexts.EventLoop
    async def schedule(self, *, execution: str, dependencies: Dict[str, Tuple[str, ...]]) -> None:
        """Schedule layers to run in sequence in the flow.

        Args:
            execution (str): ID of the execution being run.
            dependencies (Dict[Layer, Tuple[Layer, ...]]): Mapping of layers to layers it depends on.
        """

        finished: Set[str] = set()
        tasks: List[Awaitable[List[Layer]]] = []

        with contexts.Attributes(self, execution=execution):
            for layer in self.configuration.executor.queue(flow=self, dependencies=dependencies):

                # If the layer is runnable, add it to the schedule
                if set(dependencies[layer.name]).issubset(finished):
                    logger.info("Scheduling layer '%s'.", layer.name)
                    tasks.append(self.configuration.executor.schedule(layer=layer))

                # If the layer is not runnable
                else:
                    while True:
                        # Wait until the first task completes
                        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                        # Add all completed tasks to finished tasks
                        if done:
                            completed = [(await task)[0].name for task in done]
                            logger.info("Marking layers as completed: %s", sorted(completed))
                            finished.update(completed)

                        # Reset tasks to run, add waiting layer if it is runnable
                        tasks = list(pending)
                        if set(dependencies[layer.name]).issubset(finished):
                            logger.info("Scheduling layer '%s'.", layer.name)
                            tasks.append(self.configuration.executor.schedule(layer=layer))
                            break

                        if not done and not pending:
                            raise FlowError(
                                f"Stuck waiting to schedule Layer '{layer.name}'."
                                f" One of the layer dependencies '{sorted(dependencies[layer.name])}'"
                                f" has not been added to Flow '{self.name}'."
                            )

            # Wait for any remaining tasks
            await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    def register(
        self, container: layers.Container = layers.Container(), foreach: layers.ForEach = layers.ForEach()
    ) -> Callable[[LayerType], LayerType]:
        """Add a layer to the flow.

        Usage::

            @flow.register()
            class Task(Layer):
                ...
        """

        def wrapper(Layer: LayerType) -> LayerType:

            layer = Layer(configuration=layers.Configuration(container=container, foreach=foreach))

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
            layer (Union[str, Type[Layer], Layer]): Layer to get.
            **attributes (Any): Keyword attributes to add to the Layer.

        Returns:
            Layer: Layer that was registered to the flow.
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
