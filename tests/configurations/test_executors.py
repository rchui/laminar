"""Unit tests for laminar.configurations.executors"""

import asyncio
import shlex
from unittest.mock import Mock, patch

import pytest

from laminar import Layer
from laminar.configurations.executors import Docker, Executor, Thread
from laminar.exceptions import ExecutionError


@pytest.mark.asyncio
class TestExecutor:
    executor = Executor()

    async def test_sempahore(self) -> None:
        assert self.executor.semaphore._value == 1
        assert self.executor.semaphore != asyncio.Semaphore(1)

    async def test_submit(self, layer: Layer) -> None:
        with pytest.raises(NotImplementedError):
            await self.executor.submit(layer=layer)


@pytest.mark.asyncio
class TestThread:
    executor = Thread()

    async def test_submit(self) -> None:
        mock_layer = Mock()

        assert await self.executor.submit(layer=mock_layer) == mock_layer

        mock_layer.flow.execution.execute.assert_called_once_with(layer=mock_layer)


@pytest.mark.asyncio
class TestDocker:
    executor = Docker()

    async def test_submit(self, layer: Layer) -> None:
        command = shlex.split("echo 'hello world'")
        with patch("shlex.split") as mock_split:
            mock_split.return_value = command

            assert await self.executor.submit(layer=layer) == layer

        mock_split.assert_called_once_with(
            "docker run --rm --interactive --cpus 1 --env LAMINAR_EXECUTION_ID=test-execution --env"
            " LAMINAR_EXECUTION_RETRY=False --env LAMINAR_FLOW_NAME=TestFlow --env LAMINAR_LAYER_ATTEMPT=1 --env"
            " LAMINAR_LAYER_INDEX=0 --env LAMINAR_LAYER_NAME=Layer --env LAMINAR_LAYER_SPLITS=2 --memory 1500m"
            f" --volume memory:///:/laminar/.laminar --workdir /laminar {layer.configuration.container.image} python"
            " main.py"
        )

    async def test_submit_error_code(self, layer: Layer) -> None:
        command = shlex.split("exit 1")
        with patch("shlex.split") as mock_split:
            mock_split.return_value = command

            with pytest.raises(ExecutionError):
                await self.executor.submit(layer=layer)

    async def test_submit_exeception(self, layer: Layer) -> None:
        with patch("shlex.split") as mock_split:
            mock_split.side_effect = Mock(side_effect=Exception())

            with pytest.raises(Exception):
                await self.executor.submit(layer=layer)
