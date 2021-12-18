"""Configurations for laminar executors."""

import asyncio
import logging
from asyncio import Task
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple

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
    """Base scheduler"""

    async def schedule(self, *, layer: Layer, attempt: int = 1) -> List[Layer]:
        """Schedule layers for execution.

        Args:
            execution: Flow execution ID
            layer: Layer to execute
            attempt: Scheduling attempt for this layer

        Returns:
            Layer splits that were executed
        """

        try:
            splits = layer.configuration.foreach.splits(layer=layer)
            tasks: List[Task[Layer]] = []

            # Create a task per layer split
            for index in range(splits):
                instance = layer.flow.layer(layer, index=index, splits=splits, attempt=attempt)

                with hooks.context(layer=instance, annotation=hooks.annotation.schedule):
                    tasks.append(asyncio.create_task(instance.flow.configuration.executor.submit(layer=instance)))

            # Combine all tasks into a Future so they can be waited on together
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

    def runnable(
        self, *, dependencies: Dict[str, Tuple[str, ...]], pending: Set[str], finished: Set[str]
    ) -> Tuple[Set[str], Set[str]]:
        """Find all runnable layers.

        Args:
            dependencies: Layer dependencies
            pending: Pending layers
            finished: Finished layers

        Returns:
            * Remaining pending layers
            * Runnable layers
        """

        runnable = {layer for layer in pending if set(dependencies[layer]).issubset(finished)}
        return pending - runnable, runnable

    def running(self, *, flow: Flow, runnable: Set[str], running: Set["Task[List[Layer]]"]) -> Set["Task[List[Layer]]"]:
        """Schedule runnable layers.

        Args:

            flow: Flow that the layers are being run in.
            runnalbe: Runnable layers.
            running: Currently running layers.

        Returns:
            Async tasks for new and existing running layers.
        """

        return {*running, *(asyncio.create_task(self.schedule(layer=flow.layer(layer))) for layer in runnable)}

    async def wait(
        self, *, running: Set["Task[List[Layer]]"], finished: Set[str], condition: str
    ) -> Tuple[Set["Task[List[Layer]]"], Set[str]]:
        """Wait on the completion of running layers.

        Args:
            running: Running layers.
            finished: Finished layers
            condition: Condition to wait on.

        Returns:
            * Remaining running layers
            * Finished layers
        """

        # Wait until the first task completes
        completed, incomplete = await asyncio.wait(running, return_when=condition)

        # Add all completed tasks to finished tasks
        running = set(incomplete)
        finished = {*finished, *{(await task)[0].name for task in completed}}

        return running, finished

    @contexts.EventLoop
    async def loop(self, *, flow: Flow, dependencies: Dict[str, Tuple[str, ...]], finished: Set[str]) -> None:
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
        running: Set[Task[List[Layer]]] = set()

        def get_running() -> List[str]:
            return sorted(set(dependencies) - pending - finished)

        # Start the scheduling loop
        while pending:
            logger.info("Pending layers: %s", sorted(pending))
            pending, runnable = self.runnable(dependencies=dependencies, pending=pending, finished=finished)

            if not runnable and not running and pending:
                raise SchedulerError(
                    f"Stuck waiting to schedule: {sorted(pending)}."
                    f" Finished layers: {sorted(finished)}."
                    f" Remaining dependencies: { {task: sorted(dependencies[task]) for task in sorted(pending)} }"
                )

            logger.info("Runnable layers: %s", sorted(runnable))
            running = self.running(flow=flow, runnable=runnable, running=running)

            logger.info("Running layers: %s", get_running())
            running, finished = await self.wait(running=running, finished=finished, condition=asyncio.FIRST_COMPLETED)
            logger.info("Finished layers: %s", sorted(finished))

        # Finish any remaining jobs.
        if running:
            logger.info("Running layers: %s", get_running())
            running, finished = await self.wait(running=running, finished=finished, condition=asyncio.ALL_COMPLETED)
            logger.info("Finished layers: %s", sorted(finished))

    def compile(self, *, flow: Flow) -> Dict[str, Any]:
        """Compile an intermediate representation of the Flow."""

        raise NotImplementedError

    def create(self, *, ir: Dict[str, Any]) -> None:
        """Create a delegated scheduler to schedule the Flow."""

        raise NotImplementedError

    def invoke(self) -> None:
        """Invoke the delegated scheduler to start a Flow execution."""

        raise NotImplementedError


@dataclass(frozen=True)
class Delegated(Scheduler):
    """Scheduler that compiles, creates, and invokes a Flow execution on another scheduler."""


class AWS:
    @dataclass(frozen=True)
    class StepFunctions(Scheduler):
        """Schedule flows in AWS Step Functions.

        Usage::

            Flow(scheduler=AWS.StepFunctions())
        """
