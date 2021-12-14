"""Configurations for laminar executors."""

import asyncio
import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Coroutine, Dict, List, Set, Tuple

from laminar.configurations import datastores, hooks
from laminar.exceptions import SchedulerError
from laminar.types import unwrap
from laminar.utils import contexts

if TYPE_CHECKING:
    from laminar import Flow, Layer
else:
    Flow, Layer = "Flow", "Layer"


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Scheduler:
    async def schedule(self, *, layer: Layer, attempt: int = 1) -> List[Layer]:
        """Schedule layers for execution.

        Args:
            execution: Flow execution ID
            layer: Layer to execute
            attempt: Scheduling attempt for this layer

        Returns:
            Layer splits that were executed
        """

        splits = layer.configuration.foreach.splits(layer=layer)
        tasks: List[Coroutine[Any, Any, Layer]] = []

        # Create a coroutine per layer split
        for index in range(splits):
            instance = layer.flow.layer(layer, index=index, splits=splits, attempt=attempt)

            with hooks.context(layer=instance, annotation=hooks.annotation.schedule):
                tasks.append(instance.flow.configuration.executor.submit(layer=instance))

        try:
            # Combine all Coroutines into a Future so they can be waited on together
            layers = await asyncio.gather(*tasks)
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
                with hooks.context(layer=layer, annotation=hooks.annotation.retry):
                    await layer.configuration.retry.sleep(layer=layer, attempt=attempt)
                return await self.schedule(layer=layer, attempt=attempt + 1)
            raise

        # Cache the layer execution metadata
        layer.flow.configuration.datastore.write_record(
            layer=layer,
            record=datastores.Record(
                flow=datastores.Record.FlowRecord(name=layer.flow.name),
                layer=datastores.Record.LayerRecord(name=layer.name),
                execution=datastores.Record.ExecutionRecord(splits=splits),
            ),
        )

        return list(layers)

    @contexts.EventLoop
    async def run(self, *, flow: Flow, dependencies: Dict[str, Tuple[str, ...]], finished: Set[str]) -> None:
        """Run the scheduling loop.

        Args:
            flow: Flow to schedule.
            dependencies: Dependencies in the flow to schedule.
            finished: Finished layers that don't need to be scheduled.

        Raises:
            SchedulerError: If no layers are runnable and there are no running or pending layers.
        """

        dependencies = deepcopy(dependencies)
        finished = deepcopy(finished)

        logger.info("Flow: '%s'", flow.name)
        logger.info("Execution: '%s'", unwrap(flow.execution))
        logger.info("Dependencies: '%s'", dependencies)

        pending = set(dependencies) - finished
        runnable: Set[str] = set()
        running: Set[asyncio.Task[List[Layer]]] = set()

        while pending:
            logger.info("Pending layers: %s", sorted(pending))

            # Find all runnable layers
            for layer in pending:
                if set(dependencies[layer]).issubset(finished):
                    runnable.add(layer)
            pending.difference_update(runnable)

            # Schedule all runnable layers
            if runnable:
                logger.info("Runnable layers: %s", sorted(runnable))
                running.update((asyncio.create_task(self.schedule(layer=flow.layer(layer))) for layer in runnable))
                runnable = set()

            elif not runnable and not running and pending:
                raise SchedulerError(
                    f"Stuck waiting to schedule: {sorted(pending)}."
                    f" Finished layers: {sorted(finished)}."
                    f" Remaining dependencies: { {task: sorted(dependencies[task]) for task in sorted(pending)} }"
                )

            # Wait until the first task completes
            logger.info("Running layers: %s", sorted(set(dependencies) - pending - finished))
            completed, incomplete = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)

            # Add all completed tasks to finished tasks
            names = {(await task)[0].name for task in completed}
            finished.update(names)
            logger.info("Finished layers: %s", sorted(finished))

            # Reset running tasks
            running = set(incomplete)

        if running:
            # Wait for any remaining tasks
            await asyncio.wait(running, return_when=asyncio.ALL_COMPLETED)
