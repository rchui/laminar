"""Configurations for laminar executors."""

import asyncio
import logging
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Coroutine, List, Optional

from laminar.configurations import datastores, hooks
from laminar.exceptions import ExecutionError
from laminar.utils import unwrap

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"


@dataclass(frozen=True)
class Executor:
    """Generic base executor."""

    concurrency: int = 1
    timeout: Optional[int] = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Create a semaphore that limits asyncio concurrency.

        Notes:

            Concurrency is controled by Executor.concurrency

        Usage::

            async with self.semaphore:
                ...
        """

        attr = "_semaphore"
        if not hasattr(self, attr):
            object.__setattr__(self, attr, asyncio.Semaphore(self.concurrency))
        return getattr(self, attr)

    async def execute(self, *, layer: Layer) -> Layer:
        """Execute a layer.

        Args:
            layer: Layer to execute.
        """

        raise NotImplementedError

    async def schedule(self, *, layer: Layer, attempt: int = 1) -> List[Layer]:
        """Schedule a layer for execution.

        Args:
            execution: Flow execution ID
            layer: Layer to execute
            attempt: Scheduling attempt for this layer

        Returns:
            Layer splits that were executed
        """

        splits = layer.configuration.foreach.splits(layer=layer)
        tasks: List[Coroutine[Any, Any, Layer]] = []
        for index in range(splits):
            instance = layer.flow.layer(layer, index=index, splits=splits, attempt=attempt)

            with hooks.context(layer=instance, annotation=hooks.annotation.schedule):
                tasks.append(self.execute(layer=instance))

        # Cache the layer execution metadata
        layer.flow.configuration.datastore.write_record(
            layer=layer, record=datastores.Record(flow=layer.flow.name, layer=layer.name, splits=splits)
        )

        try:
            # Combine all Coroutines into a Future so they can be waited on together
            return await asyncio.gather(*tasks)
        except Exception as error:
            logger.error(
                "Encountered unexpected error: %s(%s) on attempt '%d' of '%d'.",
                type(error).__name__,
                str(error),
                attempt,
                layer.configuration.retry.attempts,
            )

            # Attempt to reschedule the layer
            if attempt < layer.configuration.retry.attempts:
                return await self.schedule(layer=layer, attempt=attempt + 1)
            raise


@dataclass(frozen=True)
class Thread(Executor):
    """Execute layers in threads."""

    async def execute(self, *, layer: Layer) -> Layer:
        async with self.semaphore:
            layer.flow.execute(execution=unwrap(layer.flow.execution), layer=layer)

            return layer


@dataclass(frozen=True)
class Docker(Executor):
    """Execute layers in Docker containers."""

    async def execute(self, *, layer: Layer) -> Layer:
        async with self.semaphore:
            workspace = f"{layer.flow.configuration.datastore.root}:{layer.configuration.container.workdir}/.laminar"

            command = " ".join(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--interactive",
                    f"--cpus {layer.configuration.container.cpu}",
                    f"--env LAMINAR_EXECUTION_ID={unwrap(layer.flow.execution)}",
                    f"--env LAMINAR_FLOW_NAME={layer.flow.name}",
                    f"--env LAMINAR_LAYER_ATTEMPT={unwrap(layer.attempt)}",
                    f"--env LAMINAR_LAYER_INDEX={unwrap(layer.index)}",
                    f"--env LAMINAR_LAYER_NAME={layer.name}",
                    f"--env LAMINAR_LAYER_SPLITS={unwrap(layer.splits)}",
                    f"--memory {layer.configuration.container.memory}m",
                    f"--volume {workspace}",
                    f"--workdir {layer.configuration.container.workdir}",
                    layer.configuration.container.image,
                    layer.configuration.container.command,
                ]
            )
            logger.debug(command)

            corou = asyncio.create_subprocess_exec(*shlex.split(command))
            task = asyncio.create_task(corou)

            try:
                process = await asyncio.wait_for(task, timeout=self.timeout)
                if await process.wait() != 0:
                    raise ExecutionError(f"Layer '{layer.name}' failed with exit code: {process.returncode}")
            except ExecutionError:
                raise
            except asyncio.TimeoutError as error:
                raise ExecutionError(f"Layer '{layer.name}' timed out after '{self.timeout}' seconds.") from error
            except Exception as error:
                message = type(error).__name__ + (f":{error}" if str(error) else "")
                raise ExecutionError(f"Layer '{layer.name}' failed with an unexpected error. {message}") from error

            return layer


class AWS:
    """Execute layers in AWS."""

    @dataclass(frozen=True)
    class Batch(Executor):
        """Execute layers in AWS Batch."""
