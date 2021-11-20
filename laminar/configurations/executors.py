"""Configurations for laminar executors."""

import logging
import shlex
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from laminar import contexts

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"


@dataclass(frozen=True)
class Executor:
    def run(self, *, execution: str, layer: Layer) -> None:
        ...


@dataclass(frozen=True)
class Thread(Executor):
    def run(self, *, execution: str, layer: Layer) -> None:

        splits = layer.configuration.foreach.size(layer=layer)
        for index in range(splits):
            with contexts.Attributes(layer, index=index, splits=splits), contexts.Attributes(
                layer.flow, execution=execution
            ):
                base_attributes = set(vars(layer))

                layer.flow.execute(layer=layer)

                execution_attributes = list(vars(layer))
                for key in execution_attributes:
                    if key not in base_attributes:
                        delattr(layer, key)


@dataclass(frozen=True)
class Docker(Executor):
    def run(self, *, execution: str, layer: Layer) -> None:
        """Execute a layer in a docker container.

        Args:
            execution (str): Flow execution ID
            layer (Layer): Layer to execute
        """

        workspace = f"{layer.flow.configuration.datastore.root}:{layer.configuration.container.workdir}/.laminar"

        splits = layer.configuration.foreach.size(layer=layer)
        for index in range(splits):
            command = " ".join(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--interactive",
                    "--tty",
                    f"--cpus {layer.configuration.container.cpu}",
                    f"--env LAMINAR_EXECUTION_ID={execution}",
                    f"--env LAMINAR_FLOW_NAME={layer.flow.name}",
                    f"--env LAMINAR_LAYER_INDEX={index}",
                    f"--env LAMINAR_LAYER_NAME={layer.name}",
                    f"--env LAMINAR_LAYER_SPLITS={splits}",
                    f"--memory {layer.configuration.container.memory}m",
                    f"--volume {workspace}",
                    f"--workdir {layer.configuration.container.workdir}",
                    layer.configuration.container.image,
                    layer.configuration.container.command,
                ]
            )
            logger.debug(command)
            subprocess.run(shlex.split(command), check=True)
