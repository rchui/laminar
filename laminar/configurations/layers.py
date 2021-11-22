"""Configurations for laminar layers."""

import inspect
import itertools
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple, Type

from laminar.configurations.datastores import Accessor, Archive

if TYPE_CHECKING:
    from laminar.components import Layer
else:
    Layer = "Layer"


@dataclass
class Container:
    """Configures a layer's container properties.

    Usage::

        @flow.layer(container=Container(...))
    """

    command: str = "python main.py"
    cpu: int = 1
    image: str = "python:3.9"
    memory: int = 1500
    workdir: str = "/laminar"

    def __post_init__(self) -> None:
        object.__setattr__(self, "workdir", self.workdir.rstrip("/"))

    def __call__(self) -> None:
        ...

    def set(self, *, layer: Layer) -> "Container":
        """Set user defined configuration.

        Returns:
            Container: User configured container configuration.
        """

        container = deepcopy(self)
        annotations: Tuple[Layer, ...] = tuple(
            parameter.annotation() for parameter in inspect.signature(container.__call__).parameters.values()
        )
        parameters = tuple(layer.flow.get_layer(layer=annotation.name) for annotation in annotations)
        container(*parameters)
        return container


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

        If `Parameter(index=None)`, ForEach will include artifacts from all Layer splits.

    Usage::

        @flow.layer(foreach=ForEach(...))
    """

    parameters: Iterable[Parameter] = field(default_factory=list)

    def join(self, *, layer: Layer, name: str) -> Archive:
        """Join together multiple artifact splits of a layer into a single Archive.

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
            instance = layer.flow.get_layer(layer=parameter.layer)
            parameters.append((instance, parameter.attribute))

            # Get archives for all layer splits.
            if parameter.index is None:
                archives.append(instance.configuration.foreach.join(layer=instance, name=parameter.attribute))

            # Get archive for specified layer index.
            else:
                archives.append(
                    instance.flow.configuration.datastore.read_archive(
                        layer=instance, index=parameter.index, name=parameter.attribute
                    )
                )

        # Compute the product of every possible set of parameter indexes based off of parameter layer splits.
        grid: List[Dict[Layer, Dict[str, int]]] = []
        for indexes in itertools.product(*(range(len(archive)) for archive in archives)):
            model: Dict[Layer, Dict[str, int]] = {}
            for (instance, attribute), index in zip(parameters, indexes):
                model.setdefault(instance, {})[attribute] = index
            grid.append(model)

        return grid

    def size(self, *, layer: Layer) -> int:
        """Get the size of the ForEach grid."""

        return len(self.grid(layer=layer))

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
                value = getattr(parameter, attribute)

                # Index only if the requested attribute is an Accessor
                value = value[index] if isinstance(value, Accessor) else value
                setattr(parameter, attribute, value)

        return parameters


@dataclass(frozen=True)
class Configuration:
    container: Container = Container()
    foreach: ForEach = ForEach()
