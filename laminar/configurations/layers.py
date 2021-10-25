"""Configurations for laminar layers."""

import itertools
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Type, Union

from dacite.core import from_dict

from laminar.configurations.datastores import Archive

if TYPE_CHECKING:
    from laminar.components import Layer
else:
    Layer = "Layer"


@dataclass(frozen=True)
class Container:
    """Configures a layer's container properties.

    Usage::

        Configuration(container=Container(...))
    """

    command: str = "python main.py"
    cpu: int = 1
    image: str = "python:3.9"
    memory: int = 1500
    workdir: str = "/laminar"

    def __post_init__(self) -> None:
        object.__setattr__(self, "workdir", self.workdir.rstrip("/"))


@dataclass(frozen=True)
class Parameter:
    """Input for configuring a ForEach."""

    layer: Type["Layer"]
    attribute: str
    index: Optional[int] = 0


@dataclass(frozen=True)
class ForEach:
    """Configures a layer to perform a grid-foreach over the configured properties.

    Notes:

        In order to foreach over each element of a layer, the layer's artifact must be sharded. See Layer.shard().

        If `Parameter(index=None)`, ForEach will include artifacts from all Layer indexes.

    Usage::

        Configuration(foreach=ForEach(...))
    """

    parameters: Iterable[Parameter] = field(default_factory=list)

    def join(self, *, layer: Layer, name: str) -> Archive:
        """Join together multiple artifact indexes of a layer into a single Archive.

        Args:
            layer (Layer): Layer to join archives for.
            name (str): Name of the attribute to join archives for.

        Returns:
            Archive: Archive created from multiple layer archives.
        """

        artifacts = [
            layer.flow.configuration.datastore.read_archive(layer=layer, index=index, name=name).artifacts
            for index in range(layer.configuration.foreach.size(layer=layer))
        ]
        return Archive(artifacts=list(itertools.chain.from_iterable(artifacts)))

    def grid(self, *, layer: Layer) -> List[Dict[Layer, Dict[str, int]]]:
        """Generate a grid of all combinations of foreach inputs.

        Args:
            layer (Layer): Layer the ForEach is configured for.

        Returns:
            List[Dict[Layer, Dict[str, int]]]: Index ordered inputs of layers mapped to attributes mapped to Accessor
                index.
        """

        parameters: List[Tuple[Layer, str]] = []
        archives: List[Archive] = []

        for parameter in self.parameters:
            instance = parameter.layer(flow=layer.flow)
            parameters.append((instance, parameter.attribute))

            # Get archives for all layer indexes.
            if parameter.index is None:
                archives.append(instance.configuration.foreach.join(layer=instance, name=parameter.attribute))

            # Get archive for specified layer index.
            else:
                archives.append(
                    instance.flow.configuration.datastore.read_archive(
                        layer=instance, index=parameter.index, name=parameter.attribute
                    )
                )

        grid: List[Dict[Layer, Dict[str, int]]] = []
        for indexes in itertools.product(*(range(len(archive.artifacts)) for archive in archives)):
            model: Dict[Layer, Dict[str, int]] = {}
            for (instance, attribute), index in zip(parameters, indexes):
                model.setdefault(instance, {})[attribute] = index
            grid.append(model)

        return grid

    def set(self, *, layer: Layer, parameters: Tuple[Layer, ...]) -> Tuple[Layer, ...]:
        """Set a foreach layer's parameters given the inputs from the foreach grid.

        Args:
            layer (Layer): Layer the ForEach is configured for.
            parameters (Tuple[Layer, ...]): Parameters in the order they will be passed to the layer.

        Returns:
            Tuple[Layer, ...]: Parameters with modified values for the foreach evaluation.
        """

        assert layer.index is not None
        inputs = self.grid(layer=layer)[layer.index]
        for parameter in parameters:
            for attribute, index in inputs.get(parameter, {}).items():
                setattr(parameter, attribute, getattr(parameter, attribute)[index])

        return parameters

    def size(self, *, layer: Layer) -> int:
        """Get the size of the ForEach grid."""

        return len(self.grid(layer=layer))


@dataclass(frozen=True)
class Configuration:
    """Configures a laminar layer.

    Usage::

        @flow.layer
        class Task(Layer, configuration=Configuration(...)):
            ...
    """

    container: Container = Container()
    foreach: ForEach = ForEach()

    def __or__(self, other: Union[Container, ForEach]) -> "Configuration":
        new: Dict[str, Any]

        if isinstance(other, Container):
            new = {"container": other}
        elif isinstance(other, ForEach):
            new = {"foreach": other}
        else:
            raise NotImplementedError

        return from_dict(Configuration, {**asdict(self), **new})
