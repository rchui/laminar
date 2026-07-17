"""Configurations for laminar executors."""

import asyncio
import hashlib
import logging
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import boto3
from mypy_boto3_batch.type_defs import (
    ContainerOverridesTypeDef,
    ContainerPropertiesTypeDef,
    JobTimeoutTypeDef,
    KeyValuePairTypeDef,
)

from laminar.exceptions import ExecutionError
from laminar.types import unwrap
from laminar.utils import contexts

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mypy_boto3_batch.client import BatchClient

    from laminar import Layer


@dataclass(frozen=True)
class Executor:
    """Generic base executor."""

    #: Number of tasks that can execute concurrently.
    concurrency: int = 1
    #: Number of seconds to wait before automatically failing.
    timeout: int = 86400

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
        semaphore: asyncio.Semaphore = getattr(self, attr)
        return semaphore

    async def submit(self, *, layer: "Layer") -> "Layer":
        """Execute a layer.

        Args:
            layer: Layer to execute.
        """

        raise NotImplementedError


@dataclass(frozen=True)
class Thread(Executor):
    """Execute layers in local threads.

    Note:

        Layers are always processed serially.

    Usage::

        Flow(executor=Thread())
    """

    async def submit(self, *, layer: "Layer") -> "Layer":
        async with self.semaphore:
            with contexts.Environment(
                LAMINAR_EXECUTION_ID=layer.execution.id,
                LAMINAR_EXECUTION_RETRY=layer.execution.retry,
                LAMINAR_FLOW_NAME=layer.execution.flow.name,
                LAMINAR_LAYER_ATTEMPT=layer.attempt,
                LAMINAR_LAYER_INDEX=layer.index,
                LAMINAR_LAYER_NAME=layer.name,
                LAMINAR_LAYER_SPLITS=layer.splits,
            ):
                layer.execution.execute(layer=layer)

            return layer


@dataclass(frozen=True)
class Docker(Executor):
    """Execute layers in local Docker containers.

    Usage::

        Flow(executor=Docker())
    """

    #: Seconds to wait for a timed-out container to be force removed before giving up on cleanup.
    STOP_TIMEOUT = 30

    async def submit(self, *, layer: "Layer") -> "Layer":
        async with self.semaphore:
            workspace = (
                f"{layer.execution.flow.configuration.datastore.root}:{layer.configuration.container.workdir}/.laminar"
            )
            # Hashed rather than interpolated directly: execution IDs are caller-supplied strings and
            # may contain spaces, slashes, or other characters that would break command tokenization or
            # be rejected as an invalid Docker container name.
            identifier = f"{layer.execution.flow.name}/{unwrap(layer.execution.id)}/{layer.name}/{layer.index}"
            name = f"laminar-{hashlib.sha256(identifier.encode()).hexdigest()}"

            # Quoted: these are joined into one string and re-split with shlex.split() below, so any
            # value containing a space or quote would otherwise corrupt tokenization of the whole
            # command, not just its own argument. container.command is intentionally left unquoted --
            # it's a shell-style string that's meant to expand to multiple argv entries.
            command = " ".join(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--interactive",
                    f"--name {name}",
                    f"--cpus {layer.configuration.container.cpu}",
                    f"--env LAMINAR_EXECUTION_ID={shlex.quote(unwrap(layer.execution.id))}",
                    f"--env LAMINAR_EXECUTION_RETRY={layer.execution.retry}",
                    f"--env LAMINAR_FLOW_NAME={shlex.quote(layer.execution.flow.name)}",
                    f"--env LAMINAR_LAYER_ATTEMPT={unwrap(layer.attempt)}",
                    f"--env LAMINAR_LAYER_INDEX={unwrap(layer.index)}",
                    f"--env LAMINAR_LAYER_NAME={shlex.quote(layer.name)}",
                    f"--env LAMINAR_LAYER_SPLITS={unwrap(layer.splits)}",
                    f"--memory {layer.configuration.container.memory}m",
                    f"--volume {shlex.quote(workspace)}",
                    f"--workdir {shlex.quote(layer.configuration.container.workdir)}",
                    shlex.quote(layer.configuration.container.image),
                    layer.configuration.container.command,
                ]
            )
            logger.debug(command)

            try:
                process = await asyncio.create_subprocess_exec(*shlex.split(command))
                returncode = await asyncio.wait_for(process.wait(), timeout=self.timeout)
                if returncode != 0:
                    raise ExecutionError(f"Layer '{layer.name}' failed with exit code: {returncode}")
                return layer
            except ExecutionError:
                raise
            except asyncio.TimeoutError as error:
                removed = await self._stop(name=name, process=process)
                message = f"Layer '{layer.name}' timed out after '{self.timeout}' seconds."
                if not removed:
                    message += f" Failed to confirm removal of container '{name}'; it may still be running."
                raise ExecutionError(message) from error
            except Exception as error:
                message = type(error).__name__ + (f":{error}" if str(error) else "")
                raise ExecutionError(f"Layer '{layer.name}' failed with an unexpected error. {message}") from error

    async def _stop(self, *, name: str, process: "asyncio.subprocess.Process") -> bool:
        """Stop a timed out container.

        Notes:
            Killing the local `docker run` client only detaches it -- the container is managed by the
            Docker daemon and keeps running (and consuming resources / writing artifacts) until it's
            explicitly stopped. `--rm` only removes a container once it has exited on its own.

        Returns:
            True if the container was confirmed removed, else False.
        """

        removed = False
        try:
            remove = await asyncio.create_subprocess_exec(
                "docker",
                "rm",
                "--force",
                name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            returncode = await asyncio.wait_for(remove.wait(), timeout=self.STOP_TIMEOUT)
            removed = returncode == 0
            if not removed:
                logger.error("'docker rm --force %s' exited with code '%d'.", name, returncode)
        except asyncio.TimeoutError:
            logger.error("Timed out after '%d' seconds waiting for 'docker rm --force %s'.", self.STOP_TIMEOUT, name)
        except Exception as error:
            logger.error("Failed to run 'docker rm --force %s': %s(%s).", name, type(error).__name__, error)

        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()

        return removed


class AWS:
    """Execute layers in AWS."""

    @dataclass(frozen=True)
    class _BatchBase:
        #: Amazon resource name (ARN) of an Batch job queue.
        job_queue_arn: str
        #: Amazon resource name (ARN) of an IAM role to attach to each Batch job.
        job_role_arn: str
        #: Poll interval wait between requesting a Batch job's status.
        poll: float = 30.0

    @dataclass(frozen=True)
    class Batch(Executor, _BatchBase):
        """Execute layers in AWS Batch.

        Usage::

            Flow(executor=AWS.Batch())
        """

        async def wait(self, *, layer: "Layer", job: str, batch: Optional["BatchClient"] = None) -> "Layer":
            """Wait on the completion of a Layer.

            Args:
                layer: Layer to wait on
                job: ID of the job the layer was submitted in
                batch: AWS Batch client

            Raises:
                ExecutionError: If the Layer does not finish successfully.
            """

            batch = batch or boto3.client("batch")

            while True:
                job_response = batch.describe_jobs(jobs=[job])
                status = job_response["jobs"][-1]["status"]

                if status == "SUCCEEDED":
                    return layer
                elif status == "FAILED":
                    raise ExecutionError(
                        f"Layer '{layer.name}' failed with status: {job_response['jobs'][0]['statusReason']}"
                    )
                else:
                    logger.info(f"Layer '{layer.name}' has status: {status}")

                await asyncio.sleep(self.poll)

        async def submit(self, *, layer: "Layer", batch: Optional["BatchClient"] = None) -> "Layer":
            async with self.semaphore:
                container = layer.configuration.container

                job_definition_hexdigest = hashlib.sha256((container.image + self.job_role_arn).encode()).hexdigest()
                job_definition_name = f"laminar-{job_definition_hexdigest}"

                batch = batch or boto3.client("batch")
                describe_response = batch.describe_job_definitions(jobDefinitionName=job_definition_name)

                # Job definition exists. Use existing one
                if describe_response["jobDefinitions"]:
                    job_definition_arn = describe_response["jobDefinitions"][-1]["jobDefinitionArn"]

                # Job definition doesn't exist. Create one.
                else:
                    logger.info("Creating job definition '%s'.", job_definition_name)
                    register_response = batch.register_job_definition(
                        jobDefinitionName=job_definition_name,
                        type="container",
                        containerProperties=ContainerPropertiesTypeDef(
                            image=container.image, jobRoleArn=self.job_role_arn
                        ),
                    )
                    job_definition_arn = register_response["jobDefinitionArn"]

                # Submit job to Batch
                submit_response = batch.submit_job(
                    jobName=f"{layer.execution.flow.name}-{layer.execution.id}-{layer.name}-{layer.index}",
                    jobDefinition=job_definition_arn,
                    jobQueue=self.job_queue_arn,
                    containerOverrides=ContainerOverridesTypeDef(
                        vcpus=container.cpu,
                        memory=container.memory,
                        command=container.command,
                        environment=[
                            KeyValuePairTypeDef(name="LAMINAR_EXECUTION_ID", value=unwrap(layer.execution.id)),
                            KeyValuePairTypeDef(name="LAMINAR_EXECUTION_RETRY", value=str(layer.execution.retry)),
                            KeyValuePairTypeDef(name="LAMINAR_FLOW_NAME", value=layer.execution.flow.name),
                            KeyValuePairTypeDef(name="LAMINAR_LAYER_ATTEMPT", value=str(unwrap(layer.attempt))),
                            KeyValuePairTypeDef(name="LAMINAR_LAYER_INDEX", value=str(unwrap(layer.index))),
                            KeyValuePairTypeDef(name="LAMINAR_LAYER_NAME", value=layer.name),
                            KeyValuePairTypeDef(name="LAMINAR_LAYER_SPLITS", value=str(unwrap(layer.splits))),
                        ],
                    ),
                    timeout=JobTimeoutTypeDef(attemptDurationSeconds=self.timeout),
                )
                job_id = submit_response["jobId"]

                # Poll for job completion
                task = asyncio.create_task(self.wait(layer=layer, job=job_id, batch=batch))
                return await asyncio.wait_for(task, timeout=self.timeout)
