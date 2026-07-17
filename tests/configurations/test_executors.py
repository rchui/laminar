"""Unit tests for laminar.configurations.executors"""

import asyncio
import hashlib
import re
import shlex
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from laminar import Layer, LayerRun
from laminar.configurations.executors import Docker, Executor, Thread
from laminar.exceptions import ExecutionError

if TYPE_CHECKING:
    from laminar import Flow


@pytest.mark.asyncio
class TestExecutor:
    executor = Executor()

    async def test_sempahore(self) -> None:
        assert self.executor.semaphore._value == 1
        assert self.executor.semaphore != asyncio.Semaphore(1)

    async def test_submit(self, layer: "LayerRun") -> None:
        with pytest.raises(NotImplementedError):
            await self.executor.submit(layer=layer)


@pytest.mark.asyncio
class TestThread:
    executor = Thread()

    async def test_submit(self) -> None:
        mock_layer = Mock()

        assert await self.executor.submit(layer=mock_layer) == mock_layer

        mock_layer.execution.execute.assert_called_once_with(layer=mock_layer)


@pytest.mark.asyncio
class TestDocker:
    executor = Docker()

    @staticmethod
    def container_name(*, flow: str, execution: str, layer: str, index: int) -> str:
        identifier = f"{flow}/{execution}/{layer}/{index}"
        return f"laminar-{hashlib.sha256(identifier.encode()).hexdigest()}"

    async def test_submit(self, layer: "LayerRun") -> None:
        command = shlex.split("echo 'hello world'")
        with patch("shlex.split") as mock_split:
            mock_split.return_value = command

            assert await self.executor.submit(layer=layer) == layer

        name = self.container_name(flow="TestFlow", execution="test-execution", layer="Layer", index=0)
        mock_split.assert_called_once_with(
            f"docker run --rm --interactive --name {name} --cpus 1 --env"
            " LAMINAR_EXECUTION_ID=test-execution --env LAMINAR_EXECUTION_RETRY=False --env"
            " LAMINAR_FLOW_NAME=TestFlow --env LAMINAR_LAYER_ATTEMPT=1 --env LAMINAR_LAYER_INDEX=0 --env"
            " LAMINAR_LAYER_NAME=Layer --env LAMINAR_LAYER_SPLITS=2 --memory 1500m --volume"
            f" memory:///:/laminar/.laminar --workdir /laminar {layer.configuration.container.image} python main.py"
        )

    async def test_submit_error_code(self, layer: "LayerRun") -> None:
        command = shlex.split("exit 1")
        with patch("shlex.split") as mock_split:
            mock_split.return_value = command

            with pytest.raises(ExecutionError):
                await self.executor.submit(layer=layer)

    async def test_submit_exeception(self, layer: "LayerRun") -> None:
        with patch("shlex.split") as mock_split:
            mock_split.side_effect = Mock(side_effect=Exception())

            with pytest.raises(Exception):
                await self.executor.submit(layer=layer)

    async def test_submit_name_survives_unsafe_execution_id(self, flow: "Flow") -> None:
        # Execution IDs are caller-supplied (Flow(...)(execution="...")) and unvalidated. A raw
        # interpolation of one into the docker command would let spaces/quotes break shlex
        # tokenization, or slashes make Docker reject the container name outright.
        flow.register(Layer)
        unsafe_layer = flow.execution('weird id/with space "quote').layer(Layer, index=0, attempt=1, splits=2)

        captured: list[str] = []
        real_split = shlex.split

        def capture_and_delegate(command: str) -> list[str]:
            captured.append(command)
            return real_split("echo hi")  # avoid actually invoking docker

        with patch("shlex.split", side_effect=capture_and_delegate):
            assert await self.executor.submit(layer=unsafe_layer) == unsafe_layer

        # Tokenizing the real (unmocked) generated command must not be corrupted by the unsafe ID.
        tokens = shlex.split(captured[0])
        name = tokens[tokens.index("--name") + 1]
        assert re.fullmatch(r"laminar-[0-9a-f]{64}", name)

        # The unsafe ID is still embedded verbatim as the env var value -- it must be a single
        # token, not have split into multiple ones and shifted every argument after it.
        env_index = tokens.index("--env")  # first --env is LAMINAR_EXECUTION_ID
        assert tokens[env_index + 1] == 'LAMINAR_EXECUTION_ID=weird id/with space "quote'
        assert tokens[-2:] == ["python", "main.py"]

    async def test_submit_timeout(self, layer: "LayerRun") -> None:
        executor = Docker(timeout=0)
        command = shlex.split("sleep 5")

        # Spawn a real "sleep" process to exercise the timeout path, but fake the "docker rm" call so
        # this test doesn't depend on a real Docker daemon being available (e.g. on macOS CI runners).
        real_create_subprocess_exec = asyncio.create_subprocess_exec

        async def fake_create_subprocess_exec(*args: str, **kwargs: Any) -> Any:
            if args[:2] == ("docker", "rm"):
                process = Mock()
                process.wait = AsyncMock(return_value=0)
                return process
            return await real_create_subprocess_exec(*args, **kwargs)

        with (
            patch("shlex.split", return_value=command),
            patch(
                "laminar.configurations.executors.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ) as mock_exec,
        ):
            with pytest.raises(ExecutionError, match="timed out") as excinfo:
                await executor.submit(layer=layer)

        assert "may still be running" not in str(excinfo.value)

        name = self.container_name(flow="TestFlow", execution="test-execution", layer="Layer", index=0)
        mock_exec.assert_any_call(
            "docker",
            "rm",
            "--force",
            name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def test_submit_timeout_cleanup_failure_is_reported(self, layer: "LayerRun") -> None:
        executor = Docker(timeout=0)
        command = shlex.split("sleep 5")

        real_create_subprocess_exec = asyncio.create_subprocess_exec

        async def fake_create_subprocess_exec(*args: str, **kwargs: Any) -> Any:
            if args[:2] == ("docker", "rm"):
                process = Mock()
                process.wait = AsyncMock(return_value=1)  # docker daemon refused / failed to remove
                return process
            return await real_create_subprocess_exec(*args, **kwargs)

        with (
            patch("shlex.split", return_value=command),
            patch(
                "laminar.configurations.executors.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
        ):
            with pytest.raises(ExecutionError, match="may still be running"):
                await executor.submit(layer=layer)

    async def test_submit_timeout_cleanup_is_bounded(self, layer: "LayerRun") -> None:
        executor = Docker(timeout=0)
        command = shlex.split("sleep 5")

        real_create_subprocess_exec = asyncio.create_subprocess_exec

        class FakeUnresponsiveProcess:
            """Doesn't resolve wait() until kill()'d, like a real process would once signalled."""

            def __init__(self) -> None:
                self._killed = asyncio.Event()

            def kill(self) -> None:
                self._killed.set()

            async def wait(self) -> int:
                await self._killed.wait()
                return -9

        async def fake_create_subprocess_exec(*args: str, **kwargs: Any) -> Any:
            if args[:2] == ("docker", "rm"):
                return FakeUnresponsiveProcess()  # unresponsive docker daemon
            return await real_create_subprocess_exec(*args, **kwargs)

        with (
            patch("shlex.split", return_value=command),
            patch(
                "laminar.configurations.executors.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
            patch.object(Docker, "STOP_TIMEOUT", 0),
        ):
            with pytest.raises(ExecutionError, match="may still be running"):
                # Bounded by STOP_TIMEOUT: fails fast rather than hanging on the unresponsive daemon.
                await asyncio.wait_for(executor.submit(layer=layer), timeout=2)

    async def test_submit_timeout_cleanup_process_is_reaped(self, layer: "LayerRun") -> None:
        executor = Docker(timeout=0)
        command = shlex.split("sleep 5")

        real_create_subprocess_exec = asyncio.create_subprocess_exec
        spawned: list[asyncio.subprocess.Process] = []

        async def fake_create_subprocess_exec(*args: str, **kwargs: Any) -> Any:
            if args[:2] == ("docker", "rm"):
                # A real, slow-to-respond process stands in for an unresponsive docker CLI, so we can
                # verify it actually gets killed rather than just having its wait() cancelled.
                process = await real_create_subprocess_exec(
                    "sleep", "10", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                spawned.append(process)
                return process
            return await real_create_subprocess_exec(*args, **kwargs)

        with (
            patch("shlex.split", return_value=command),
            patch(
                "laminar.configurations.executors.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
            patch.object(Docker, "STOP_TIMEOUT", 0),
        ):
            with pytest.raises(ExecutionError, match="may still be running"):
                await asyncio.wait_for(executor.submit(layer=layer), timeout=5)

        assert len(spawned) == 1
        # A non-None returncode means the process was actually killed and waited on, not just
        # abandoned when asyncio.wait_for() cancelled its wait() coroutine.
        assert spawned[0].returncode is not None
