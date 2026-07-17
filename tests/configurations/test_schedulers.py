"""Unit tests for laminar.configurations.schedulers"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import Mock, patch

import pytest

from laminar import Layer
from laminar.configurations.datastores import Record
from laminar.configurations.schedulers import Scheduler


@asynccontextmanager
async def coroutine(path: str) -> AsyncGenerator[Mock, None]:
    async def func(*args: Any, **kwargs: Any) -> None: ...

    with patch(path) as mock:
        mock.return_value = func
        yield mock


class TestScheduler:
    scheduler = Scheduler()

    @pytest.mark.asyncio
    async def test_schedule(self, layer: Layer) -> None:
        async with coroutine("laminar.configurations.executors.Thread.submit") as mock_execute:
            await self.scheduler.schedule(layer=layer)

            mock_execute.assert_called_once_with(layer=layer)

        assert layer.execution.flow.configuration.datastore.read_record(layer=layer) == Record(
            flow=Record.FlowRecord(name="TestFlow"),
            layer=Record.LayerRecord(name="Layer"),
            execution=Record.ExecutionRecord(splits=1),
        )

    @pytest.mark.asyncio
    async def test_schedule_cancels_siblings_on_failure(self, layer: Layer) -> None:
        async def submit(*, layer: Layer) -> Layer:
            if layer.index == 0:
                raise RuntimeError("boom")
            await asyncio.sleep(10)
            return layer

        with (
            patch("laminar.configurations.layers.ForEach.splits", return_value=2),
            patch("laminar.configurations.executors.Thread.submit", side_effect=submit),
            pytest.raises(RuntimeError),
        ):
            await self.scheduler.schedule(layer=layer)

        # The still-sleeping sibling split must be cancelled, not abandoned running in the background.
        current = asyncio.current_task()
        leaked = [task for task in asyncio.all_tasks() if task is not current and not task.done()]
        assert leaked == []

    def test_runnable(self) -> None:
        class A(Layer): ...

        class B(Layer):
            def __call__(self, a: A) -> None: ...

        class C(Layer):
            def __call__(self, a: A) -> None: ...

        dependencies: dict[str, set[str]] = {"A": set(), "B": {"A"}, "C": {"A"}}

        # Just starting
        pending, runnable = self.scheduler.runnable(dependencies=dependencies, pending={"A", "B", "C"}, finished=set())

        assert runnable == {"A"}
        assert pending == {"B", "C"}

        # Partially complete
        pending, runnable = self.scheduler.runnable(dependencies=dependencies, pending={"B", "C"}, finished={"A"})

        assert runnable == {"B", "C"}
        assert pending == set()

        # Partially complete
        pending, runnable = self.scheduler.runnable(dependencies=dependencies, pending={"C"}, finished={"A", "B"})

        assert runnable == {"C"}
        assert pending == set()

        # All complete
        pending, runnable = self.scheduler.runnable(dependencies=dependencies, pending=set(), finished={"A", "B", "C"})

        assert runnable == set()
        assert pending == set()
