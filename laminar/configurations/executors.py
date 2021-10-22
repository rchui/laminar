"""Configurations for laminar executors."""

import logging
import shlex
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"


@dataclass(frozen=True)
class Executor:
    def run(self, execution_id: str, layer: Layer) -> None:
        ...


@dataclass(frozen=True)
class Docker(Executor):
    def run(self, execution_id: str, layer: Layer) -> None:
        """Execute a layer in a docker container.

        Args:
            execution_id (str): Flow execution ID
            layer (Layer): Layer to execute
        """

        command = " ".join(
            [
                "docker",
                "run",
                "--rm",
                "--interactive",
                "--tty",
                f"--cpus {layer.container.cpu}",
                f"--env LAMINAR_EXECUTION_ID={execution_id}",
                f"--env LAMINAR_FLOW_NAME={layer.flow.name}",
                f"--env LAMINAR_LAYER_NAME={layer.name}",
                f"--memory {layer.container.memory}m",
                f"--volume {layer.flow.datastore.root}:{layer.container.workdir}/.laminar",
                f"--workdir {layer.container.workdir}",
                layer.container.image,
                layer.container.command,
            ]
        )
        logger.debug(command)
        subprocess.run(shlex.split(command), check=True)
