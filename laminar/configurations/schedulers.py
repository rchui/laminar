"""Configurations for laminar executors."""

import asyncio
import functools
import logging
import operator
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple

from laminar.configurations import datastores, hooks
from laminar.exceptions import SchedulerError
from laminar.types import unwrap
from laminar.utils import contexts

if TYPE_CHECKING:
    from asyncio import Task

    from laminar import Execution, Layer


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Scheduler:
    """Base scheduler"""

    async def schedule(self, *, layer: "Layer", attempt: int = 1) -> List["Layer"]:
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
            tasks: List["Task[Layer]"] = []

            # Create a task per layer split
            for index in range(splits):
                instance = layer.execution.layer(layer, index=index, splits=splits, attempt=attempt)

                with hooks.event.context(layer=instance, annotation=hooks.annotation.submission):
                    tasks.append(
                        asyncio.create_task(instance.execution.flow.configuration.executor.submit(layer=instance))
                    )

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
                with hooks.event.context(layer=layer, annotation=hooks.annotation.retry):
                    await layer.configuration.retry.sleep(layer=layer, attempt=attempt)
                return await self.schedule(layer=layer, attempt=attempt + 1)
            raise

        # Cache the layer execution metadata
        layer.execution.flow.configuration.datastore.write_record(
            layer=layer,
            record=datastores.Record(
                flow=datastores.Record.FlowRecord(name=layer.execution.flow.name),
                layer=datastores.Record.LayerRecord(name=layer.name),
                execution=datastores.Record.ExecutionRecord(splits=splits),
            ),
        )

        return list(layers)

    def runnable(
        self, *, dependencies: Dict[str, Set[str]], pending: Set[str], finished: Set[str]
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

        runnable = {layer for layer in pending if dependencies[layer].issubset(finished)}
        return pending - runnable, runnable

    def skippable(self, *, execution: "Execution", runnable: Set[str], finished: Set[str]) -> Tuple[Set[str], Set[str]]:
        """Find all skippable layers.

        Args:
            execution: Execution being schedule.
            runnable: Runnable layers.
            finished: Finished layers.

        Returns:
            * Runnable layers
            * Finished layers
        """

        skippable: Set[str] = set()

        for layer in runnable:
            instance = execution.layer(layer)

            # Check for retries
            if instance.execution.retry and instance.state.finished:
                skippable.add(layer)
                continue

            # Check entry hooks
            conditions = hooks.condition.gather(layer=instance, annotation=hooks.annotation.entry)
            if not functools.reduce(operator.and_, conditions, True):
                skippable.add(layer)
                continue

            # Check dependencies if not conditions exist
            if not conditions and not all(dependency.state.finished for dependency in instance._dependencies):
                skippable.add(layer)
                continue

        if skippable:
            logger.info("Skipping layers: %s", sorted(skippable))
        return runnable - skippable, finished | skippable

    def running(
        self, *, execution: "Execution", runnable: Set[str], running: Set["Task[List[Layer]]"]
    ) -> Set["Task[List[Layer]]"]:
        """Schedule runnable layers.

        Args:

            execution: Execution that the layers are being run in.
            runnalbe: Runnable layers.
            running: Currently running layers.

        Returns:
            Async tasks for new and existing running layers.
        """

        return running | {asyncio.create_task(self.schedule(layer=execution.layer(layer))) for layer in runnable}

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
        finished = finished | {(await task)[0].name for task in completed}

        return running, finished

    @contexts.EventLoop
    async def loop(self, *, execution: "Execution", dependencies: Dict[str, Set[str]], finished: Set[str]) -> None:
        """Run the scheduling loop.

        Args:
            execution: Flow execution to schedule.
            dependencies: Dependencies in the flow to schedule.
            finished: Finished layers that don't need to be scheduled.

        Raises:
            SchedulerError: If no layers are runnable and there are no running or pending layers.
        """

        dependencies = deepcopy(dependencies)
        finished = deepcopy(finished)

        logger.info("Flow: '%s'", execution.flow.name)
        logger.info("Execution: '%s'", unwrap(execution.id))
        logger.info("Dependencies: '%s'", dependencies)

        pending = set(dependencies) - finished
        runnable: Set[str] = set()
        running: Set["Task[List[Layer]]"] = set()

        # Start the scheduling loop
        while pending:
            logger.info("Pending layers: %s", sorted(pending))
            pending, runnable = self.runnable(dependencies=dependencies, pending=pending, finished=finished)

            # There are pending layers but nothing is runnable or running.
            if not runnable and not running and pending:
                raise SchedulerError(
                    f"Stuck waiting to schedule: {sorted(pending)}."
                    f" Finished layers: {sorted(finished)}."
                    f" Remaining dependencies: { {task: sorted(dependencies[task]) for task in sorted(pending)} }"
                )

            logger.info("Runnable layers: %s", sorted(runnable))
            runnable, finished = self.skippable(execution=execution, runnable=runnable, finished=finished)

            running = self.running(execution=execution, runnable=runnable, running=running)

            # Determine async task wait condition
            condition = asyncio.FIRST_COMPLETED if pending else asyncio.ALL_COMPLETED

            logger.info("Running layers: %s", sorted(set(dependencies) - pending - finished))
            if running:
                running, finished = await self.wait(running=running, finished=finished, condition=condition)
            logger.info("Finished layers: %s", sorted(finished))

    def compile(self, *, execution: "Execution") -> Dict[str, Any]:
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
