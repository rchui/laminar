import inspect
from typing import Any, Dict, Set, Type, TypeVar

from laminar.configurations.layers import Container
from laminar.exceptions import FlowError


class Layer:
    """Task to execute as part of a flow.

    Usage::

        from laminar import Layer

        class Task(Layer):
            ...
    """

    container: Container

    def __init_subclass__(cls, container: Container = Container()) -> None:
        cls.container = container

    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    @property
    def name(self) -> str:
        return type(self).__name__

    def __call__(self) -> None:
        ...


LayerType = TypeVar("LayerType", bound=Type[Layer])


class Flow:
    """Collection of tasks that execute in a specific order.

    Usage::

        from laminar import Flow, Layer

        flow = Flow(name="HelloFlow")
    """

    def __init__(self, *, name: str) -> None:
        """
        Args:
            name (str): Name of the flow. Must be alphanumeric.

        Raises:
            FlowError: If the flow's name is not alphanumeric
        """

        if not name.isalnum():
            raise FlowError(f"A flow's name can only contain alphanumeric characters. Given name '{name}'.")

        self.name = name

        self._dependencies: Dict[Layer, Set[Layer]] = {}

    @property
    def dependencies(self) -> Dict[str, Set[str]]:
        return {child.name: {parent.name for parent in parents} for child, parents in self._dependencies.items()}

    @property
    def dependents(self) -> Dict[str, Set[str]]:
        dependents: Dict[str, Set[str]] = {}
        for child, parents in self._dependencies.items():
            for parent in parents:
                dependents.setdefault(parent.name, set()).add(child.name)
        return dependents

    def layer(self, Layer: LayerType) -> LayerType:
        """Add a layer to the flow.

        Usage::

            @flow.layer
            class Task(Layer):
                ...
        """

        layer = Layer()

        if layer in self._dependencies:
            raise FlowError(f"Duplicate layer added to flow '{self.name}'. Given layer '{layer.name}'.")

        self._dependencies[layer] = set()

        for parameter in inspect.signature(layer.__call__).parameters.values():
            self._dependencies[layer].add(parameter.annotation())

        return Layer


# class Flow(BaseModel):
#     datasource: DataSource = DataSource()
#     id: str = current.execution.id or str(Ksuid())

#     dag: Dict[Type[Layer], Set[Type[Layer]]] = Field(default_factory=dict)
#     mapping: Dict[str, Type[Layer]] = Field(default_factory=dict)

#     def __init__(__pydantic_self__, **data: Any) -> None:
#         super().__init__(**data)

#     @property
#     def _dependencies(self) -> Dict[str, str]:
#         return {
#             child.__name__: {parent.__name__ for parent in parents} for child, parents in self._dependencies.items()
#         }

#     @property
#     def name(self) -> str:
#         return self.__repr_name__()

#     def __call__(self) -> None:
#         def get_pending(dag: Dict[str, str], finished: Set[str]) -> Set[Type[Layer]]:
#             return {self.mapping[name] for name, parents in dag.items() if parents.issubset(finished)}

#         if current.layer.name is not None:
#             layer = self.mapping[current.layer.name]

#             configuration: Configuration = layer.configuration

#             parameters = {
#                 artifact: self.datasource.read(self.datasource.uri(self.name, self.id, source.__name__), artifact)
#                 for artifact, source in configuration.dependencies.data.items()
#             }

#             run = layer(configuration=configuration, **parameters)

#             run()

#             for artifact, value in vars(run).items():
#                 if artifact != "configuration":
#                     self.datasource.write(self.datasource.uri(self.name, self.id, layer.__name__), artifact, value)

#         else:
#             dag = self.dag
#             finished: Set[str] = set()

#             pending = get_pending(dag, finished)

#             while pending:
#                 for layer in pending:

#                     configuration: Configuration = layer.configuration

#                     archive = (
#                         f"{os.getcwd()}/{self.datasource.root}:{configuration.container.workdir}/{self.datasource.root}"
#                     )
#                     command = " ".join(
#                         [
#                             "docker",
#                             "run",
#                             "--rm",
#                             "--interactive",
#                             "--tty",
#                             f"--env LAMINAR_EXECUTION_ID={self.id}",
#                             f"--env LAMINAR_LAYER_NAME={layer.__name__}",
#                             f"--volume {archive}",
#                             f"--workdir {configuration.container.workdir}",
#                             configuration.container.image,
#                             configuration.container.command,
#                         ]
#                     )
#                     logger.info(command)
#                     subprocess.run(shlex.split(command), check=True)

#                     finished.add(layer.__name__)
#                     dag.pop(layer.__name__)

#                 pending = get_pending(dag, finished)

#                 if not pending and dag:
#                     raise FlowError(
#                         f"A dependency exists for a step that is not registered with the {self.name} flow. "
#                         f"Finished steps: {sorted(finished)}. "
#                         f"Remaining dag: {dag}."
#                     )

#     def layer(self, layer: LayerType) -> LayerType:
#         if layer.__name__ in self.mapping:
#             raise FlowError(f"The {layer.__name__} layer is being added more than once to the {self.name} flow.")

#         self.mapping[layer.__name__] = layer
#         self._dependencies[layer] = {
#             *layer.configuration.dependencies.layers,
#             *layer.configuration.dependencies.data.values(),
#         }

#         return layer
