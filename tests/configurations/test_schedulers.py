"""Unit tests for laminar.configurations.schedulers"""

from contextlib import contextmanager
from typing import Any, Generator
from unittest.mock import Mock, patch

import pytest

from laminar import Layer
from laminar.configurations.datastores import Record
from laminar.configurations.schedulers import Scheduler


@contextmanager
def coroutine(path: str) -> Generator[Mock, None, None]:
    async def func(*args: Any, **kwargs: Any) -> None:
        ...

    with patch(path) as mock:
        mock.return_value = func()
        yield mock


@pytest.mark.asyncio
class TestScheduler:
    scheduler = Scheduler()

    async def test_schedule(self, layer: Layer) -> None:
        with coroutine("laminar.configurations.executors.Thread.submit") as mock_execute:
            await self.scheduler.schedule(layer=layer)

            mock_execute.assert_called_once_with(layer=layer)

        assert layer.flow.configuration.datastore.read_record(layer=layer) == Record(
            flow=Record.FlowRecord(name="TestFlow"),
            layer=Record.LayerRecord(name="Layer"),
            execution=Record.ExecutionRecord(splits=1),
        )
