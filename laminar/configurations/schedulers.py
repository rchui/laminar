"""Configurations for laminar executors."""

import asyncio
import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Set, Tuple

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
    @contexts.EventLoop
    async def run(self, *, flow: Flow, dependencies: Dict[str, Tuple[str, ...]], finished: Set[str]) -> None:
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
                running.update(
                    (
                        asyncio.create_task(flow.configuration.executor.schedule(layer=flow.layer(layer)))
                        for layer in runnable
                    )
                )
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
