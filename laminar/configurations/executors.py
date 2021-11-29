"""Configurations for laminar executors."""

import logging
import shlex
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Generator, Tuple

import toposort

from laminar.configurations import datastores, hooks

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from laminar import Flow, Layer
else:
    Flow = "Flow"
    Layer = "Layer"


@dataclass(frozen=True)
class Executor:
    concurrency: int = 1

    def schedule(self, *, execution: str, layer: Layer) -> None:
        ...

    def queue(self, *, flow: Flow, dependencies: Dict[str, Tuple[str, ...]]) -> Generator[Layer, None, None]:
        """Get layers in a topologically sorted order.

        Args:
            flow: Flow to sort layers for.
            dependencies: Layers mapped to layers they're dependent on.

        Yields:
            Sorted layers.
        """

        for name in toposort.toposort_flatten(dependencies):
            yield flow.layer(name)


@dataclass(frozen=True)
class Thread(Executor):
    def schedule(self, *, execution: str, layer: Layer) -> None:
        """Execute a layer in a thread.

        Args:
            execution (str): Flow execution ID
            layer (Layer): Layer to execute
        """

        splits = layer.configuration.foreach.splits(layer=layer)
        for index in range(splits):
            instance = layer.flow.layer(layer, index=index, splits=splits)

            with hooks.context(layer=instance, annotation=hooks.annotation.schedule):
                instance.flow.execute(execution=execution, layer=instance)

        # Cache the layer execution metadata
        layer.flow.configuration.datastore.write_record(
            layer=layer, record=datastores.Record(flow=layer.flow.name, layer=layer.name, splits=splits)
        )


@dataclass(frozen=True)
class Docker(Executor):
    def schedule(self, *, execution: str, layer: Layer) -> None:
        """Execute a layer in a docker container.

        Args:
            execution (str): Flow execution ID
            layer (Layer): Layer to execute
        """

        workspace = f"{layer.flow.configuration.datastore.root}:{layer.configuration.container.workdir}/.laminar"

        splits = layer.configuration.foreach.splits(layer=layer)
        for index in range(splits):
            instance = layer.flow.layer(layer, index=index, splits=splits)

            with hooks.context(layer=instance, annotation=hooks.annotation.schedule):
                command = " ".join(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--interactive",
                        "--tty",
                        f"--cpus {instance.configuration.container.cpu}",
                        f"--env LAMINAR_EXECUTION_ID={execution}",
                        f"--env LAMINAR_FLOW_NAME={instance.flow.name}",
                        f"--env LAMINAR_LAYER_INDEX={index}",
                        f"--env LAMINAR_LAYER_NAME={instance.name}",
                        f"--env LAMINAR_LAYER_SPLITS={splits}",
                        f"--memory {instance.configuration.container.memory}m",
                        f"--volume {workspace}",
                        f"--workdir {instance.configuration.container.workdir}",
                        instance.configuration.container.image,
                        instance.configuration.container.command,
                    ]
                )
                logger.debug(command)
                subprocess.run(shlex.split(command), check=True)

        # Cache the layer execution metadata
        layer.flow.configuration.datastore.write_record(
            layer=layer, record=datastores.Record(flow=layer.flow.name, layer=layer.name, splits=splits)
        )


class AWS:
    @dataclass(frozen=True)
    class Batch(Executor):
        ...


aws = AWS()
