"""Configurations for laminar layers."""

import itertools
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple, Type

from laminar.configurations import datastores
from laminar.utils import unwrap

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """Configures a layer's container properties.

    Usage::

        @flow.register(container=Container(...))
    """

    command: str = "python main.py"
    cpu: int = 1
    image: str = "python:3.9"
    memory: int = 1500
    workdir: str = "/laminar"

    def __post_init__(self) -> None:
        if not self.workdir.endswith(("://", ":///")):
            object.__setattr__(self, "workdir", self.workdir.rstrip("/"))


@dataclass
class Parameter:
    """Input for configuring a ForEach."""

    layer: Type["Layer"]
    attribute: str
    index: Optional[int] = 0


@dataclass
class ForEach:
    """Configures a layer to perform a grid-foreach over the configured properties.

    Notes:

        In order to foreach over each element of a layer, the layer's artifact must be sharded. See Layer.shard().

        If `Parameter(index=None)`, ForEach will include artifacts from all Layer splits.

    Usage::

        @flow.register(foreach=ForEach(...))
    """

    parameters: Iterable[Parameter] = field(default_factory=list)

    def join(self, *, layer: Layer, name: str) -> datastores.Archive:
        """Join together multiple artifact splits of a layer into a single Archive.

        Args:
            layer (Layer): Layer to join archives for.
            name (str): Name of the attribute to join archives for.

        Returns:
            datastores.Archive: Archive created from multiple layer archives.
        """

        datastore = layer.flow.configuration.datastore
        cache_path = datastores.Archive.path(layer=layer, index=0, name=name, cache=True)

        if datastore.exists(path=cache_path):
            logger.debug("Cache hit for layer '%s', archive '%s'.", layer.name, name)
            archive = datastore._read_archive(path=cache_path)

        else:
            logger.debug("Cache miss for layer '%s', archive '%s'.", layer.name, name)
            artifacts = [
                datastore.read_archive(layer=layer, index=index, name=name).artifacts
                for index in range(layer.configuration.foreach.splits(layer=layer))
            ]
            archive = datastores.Archive(artifacts=list(itertools.chain.from_iterable(artifacts)))

            datastore._write_archive(path=cache_path, archive=archive)

        return archive

    def grid(self, *, layer: Layer) -> List[Dict[Layer, Dict[str, int]]]:
        """Generate a grid of all combinations of foreach inputs.

        Args:
            layer (Layer): Layer the ForEach is configured for.

        Returns:
            List[Dict[Layer, Dict[str, int]]]: Index ordered inputs of layers mapped to attributes mapped to Accessor
                index.
        """

        parameters: List[Tuple[Layer, str]] = []
        archives: List[datastores.Archive] = []

        for parameter in self.parameters:
            instance = layer.flow.layer(parameter.layer)
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

    def splits(self, *, layer: Layer) -> int:
        """Get the splits of the ForEach grid."""

        if layer.flow.configuration.datastore.exists(path=datastores.Record.path(layer=layer)):
            logger.debug("Cache hit for layer '%s' record.", layer.name)
            return layer.flow.configuration.datastore.read_record(layer=layer).splits

        else:
            logger.debug("Cache miss for layer '%s' record.", layer.name)
            return len(self.grid(layer=layer))

    def set(self, *, layer: Layer, parameters: Tuple[Layer, ...]) -> Tuple[Layer, ...]:
        """Set a foreach layer's parameters given the inputs from the foreach grid.

        Args:
            layer (Layer): Layer the ForEach is configured for.
            parameters (Tuple[Layer, ...]): Parameters in the order they will be passed to the layer.

        Returns:
            Tuple[Layer, ...]: Parameters with modified values for the foreach evaluation.
        """

        inputs = self.grid(layer=layer)[unwrap(layer.index)]
        for parameter in parameters:
            for attribute, index in inputs.get(parameter, {}).items():
                value = getattr(parameter, attribute)

                # Index only if the requested attribute is an Accessor
                value = value[index] if isinstance(value, datastores.Accessor) else value
                setattr(parameter, attribute, value)

        return parameters


@dataclass
class Retry:
    attempts: int = 1


@dataclass
class Configuration:
    container: Container = Container()
    foreach: ForEach = ForEach()
    retry: Retry = Retry()
