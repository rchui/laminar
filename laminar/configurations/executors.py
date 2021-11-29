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

    def execute(self, layer: Layer) -> None:
        """Execute a layer.

        Args:
            layer: Layer to execute.
        """

    def schedule(self, *, layer: Layer) -> None:
        """Schedule a layer for execution.

        Args:
            execution (str): Flow execution ID
            layer (Layer): Layer to execute
        """

        splits = layer.configuration.foreach.splits(layer=layer)
        for index in range(splits):
            instance = layer.flow.layer(layer, index=index, splits=splits)

            with hooks.context(layer=instance, annotation=hooks.annotation.schedule):
                self.execute(layer=instance)

        # Cache the layer execution metadata
        layer.flow.configuration.datastore.write_record(
            layer=layer, record=datastores.Record(flow=layer.flow.name, layer=layer.name, splits=splits)
        )


@dataclass(frozen=True)
class Thread(Executor):
    """Execute layers in threads."""

    def execute(self, layer: Layer) -> None:
        assert layer.flow.execution is not None
        layer.flow.execute(execution=layer.flow.execution, layer=layer)


@dataclass(frozen=True)
class Docker(Executor):
    """Execute layers in Docker containers."""

    def execute(self, layer: Layer) -> None:
        assert layer.index is not None
        assert layer.splits is not None
        assert layer.flow.execution is not None

        workspace = f"{layer.flow.configuration.datastore.root}:{layer.configuration.container.workdir}/.laminar"

        command = " ".join(
            [
                "docker",
                "run",
                "--rm",
                "--interactive",
                "--tty",
                f"--cpus {layer.configuration.container.cpu}",
                f"--env LAMINAR_EXECUTION_ID={layer.flow.execution}",
                f"--env LAMINAR_FLOW_NAME={layer.flow.name}",
                f"--env LAMINAR_LAYER_INDEX={layer.index}",
                f"--env LAMINAR_LAYER_NAME={layer.name}",
                f"--env LAMINAR_LAYER_SPLITS={layer.splits}",
                f"--memory {layer.configuration.container.memory}m",
                f"--volume {workspace}",
                f"--workdir {layer.configuration.container.workdir}",
                layer.configuration.container.image,
                layer.configuration.container.command,
            ]
        )
        logger.debug(command)
        subprocess.run(shlex.split(command), check=True)


class AWS:
    """Execute layers in AWS."""

    @dataclass(frozen=True)
    class Batch(Executor):
        """Execute layers in AWS Batch."""


aws = AWS()
