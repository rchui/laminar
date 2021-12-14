"""Unit tests for laminar.configurations.executors"""

import asyncio
import shlex
from contextlib import contextmanager
from typing import Any, Generator
from unittest.mock import Mock, patch

import pytest

from laminar import Layer
from laminar.configurations.datastores import Record
from laminar.configurations.executors import Docker, Executor, Thread
from laminar.exceptions import ExecutionError


@contextmanager
def coroutine(path: str) -> Generator[Mock, None, None]:
    async def func(*args: Any, **kwargs: Any) -> None:
        ...

    with patch(path) as mock:
        mock.return_value = func()
        yield mock


@pytest.mark.asyncio
class TestExecutor:
    executor = Executor()

    async def test_sempahore(self) -> None:
        assert self.executor.semaphore._value == 1
        assert self.executor.semaphore != asyncio.Semaphore(1)

    async def test_execute(self, layer: Layer) -> None:
        with pytest.raises(NotImplementedError):
            await self.executor.submit(layer=layer)

    async def test_schedule(self, layer: Layer) -> None:
        with coroutine("laminar.configurations.executors.Executor.submit") as mock_execute:
            await self.executor.schedule(layer=layer)

            mock_execute.assert_called_once_with(layer=layer)

        assert layer.flow.configuration.datastore.read_record(layer=layer) == Record(
            flow=Record.FlowRecord(name="TestFlow"),
            layer=Record.LayerRecord(name="Layer"),
            execution=Record.ExecutionRecord(splits=1),
        )


@pytest.mark.asyncio
class TestThread:
    executor = Thread()

    async def test_execute(self) -> None:
        mock_layer = Mock()

        assert await self.executor.submit(layer=mock_layer) == mock_layer

        mock_layer.flow.execute.assert_called_once_with(execution=mock_layer.flow.execution, layer=mock_layer)


@pytest.mark.asyncio
class TestDocker:
    executor = Docker()

    async def test_execute(self, layer: Layer) -> None:
        command = shlex.split("echo 'hello world'")
        with patch("shlex.split") as mock_split:
            mock_split.return_value = command

            assert await self.executor.submit(layer=layer) == layer

        mock_split.assert_called_once_with(
            "docker run --rm --interactive --cpus 1 --env LAMINAR_EXECUTION_ID=test-execution --env"
            " LAMINAR_FLOW_NAME=TestFlow --env LAMINAR_LAYER_ATTEMPT=1 --env LAMINAR_LAYER_INDEX=0 --env"
            " LAMINAR_LAYER_NAME=Layer --env LAMINAR_LAYER_SPLITS=2 --memory 1500m --volume"
            " memory:///:/laminar/.laminar --workdir /laminar python:3.9 python main.py"
        )

    async def test_execute_error_code(self, layer: Layer) -> None:
        command = shlex.split("exit 1")
        with patch("shlex.split") as mock_split:
            mock_split.return_value = command

            with pytest.raises(ExecutionError):
                await self.executor.submit(layer=layer)

    async def test_execute_exeception(self, layer: Layer) -> None:
        with patch("shlex.split") as mock_split:
            mock_split.side_effect = Mock(side_effect=Exception())

            with pytest.raises(Exception):
                await self.executor.submit(layer=layer)
