"""Configurations for laminar executors."""

import logging
import shlex
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Executor(ABC):
    ...

    @abstractmethod
    def run(self, execution_id: str) -> None:
        ...


@dataclass(frozen=True)
class Docker(Executor):
    def run(self, execution_id: str, layer: Any) -> None:
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
                f"--volume {layer.flow.datasource.root}:{layer.container.workdir}/.laminar",
                f"--workdir {layer.container.workdir}",
                layer.container.image,
                layer.container.command,
            ]
        )
        logger.debug(command)
        subprocess.run(shlex.split(command), check=True)
