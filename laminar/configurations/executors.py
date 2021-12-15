"""Configurations for laminar executors."""

import asyncio
import hashlib
import logging
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import boto3
from mypy_boto3_batch.client import BatchClient
from mypy_boto3_batch.type_defs import ContainerOverridesTypeDef, ContainerPropertiesTypeDef, JobTimeoutTypeDef

from laminar.exceptions import ExecutionError
from laminar.types import unwrap

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from laminar import Layer
else:
    Layer = "Layer"


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

    async def submit(self, *, layer: Layer) -> Layer:
        """Execute a layer.

        Args:
            layer: Layer to execute.
        """

        raise NotImplementedError


@dataclass(frozen=True)
class Thread(Executor):
    """Execute layers in threads.

    Usage::

        Flow(executor=Thread())
    """

    async def submit(self, *, layer: Layer) -> Layer:
        async with self.semaphore:
            layer.flow.execute(execution=unwrap(layer.flow.execution), layer=layer)

            return layer


@dataclass(frozen=True)
class Docker(Executor):
    """Execute layers in Docker containers.

    Usage::

        Flow(executor=Docker())
    """

    async def submit(self, *, layer: Layer) -> Layer:
        async with self.semaphore:
            workspace = f"{layer.flow.configuration.datastore.root}:{layer.configuration.container.workdir}/.laminar"

            command = " ".join(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--interactive",
                    f"--cpus {layer.configuration.container.cpu}",
                    f"--env LAMINAR_EXECUTION_ID={unwrap(layer.flow.execution)}",
                    f"--env LAMINAR_FLOW_NAME={layer.flow.name}",
                    f"--env LAMINAR_LAYER_ATTEMPT={unwrap(layer.attempt)}",
                    f"--env LAMINAR_LAYER_INDEX={unwrap(layer.index)}",
                    f"--env LAMINAR_LAYER_NAME={layer.name}",
                    f"--env LAMINAR_LAYER_SPLITS={unwrap(layer.splits)}",
                    f"--memory {layer.configuration.container.memory}m",
                    f"--volume {workspace}",
                    f"--workdir {layer.configuration.container.workdir}",
                    layer.configuration.container.image,
                    layer.configuration.container.command,
                ]
            )
            logger.debug(command)

            task = asyncio.create_task(asyncio.create_subprocess_exec(*shlex.split(command)))

            try:
                process = await asyncio.wait_for(task, timeout=self.timeout)
                if await process.wait() != 0:
                    raise ExecutionError(f"Layer '{layer.name}' failed with exit code: {process.returncode}")
                return layer
            except ExecutionError:
                raise
            except asyncio.TimeoutError as error:
                raise ExecutionError(f"Layer '{layer.name}' timed out after '{self.timeout}' seconds.") from error
            except Exception as error:
                message = type(error).__name__ + (f":{error}" if str(error) else "")
                raise ExecutionError(f"Layer '{layer.name}' failed with an unexpected error. {message}") from error


class AWS:
    """Execute layers in AWS."""

    @dataclass(frozen=True)
    class BaseBatch:
        job_queue_arn: str
        job_role_arn: str
        poll: float = 30.0

    @dataclass(frozen=True)
    class Batch(Executor, BaseBatch):
        """Execute layers in AWS Batch.

        Usage::

            Flow(executor=AWS.Batch())
        """

        async def wait(self, *, layer: Layer, job: str, batch: Optional[BatchClient] = None) -> Layer:
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

        async def submit(self, *, layer: Layer, batch: Optional[BatchClient] = None) -> Layer:
            async with self.semaphore:
                container = layer.configuration.container

                job_definition_hexdigest = hashlib.sha256((container.image + self.job_role_arn).encode()).hexdigest()
                job_definition_name = f"laminar_{job_definition_hexdigest}"

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
                    jobName=f"{layer.flow.name}-{layer.flow.execution}-{layer.name}-{layer.index}",
                    jobDefinition=job_definition_arn,
                    jobQueue=self.job_queue_arn,
                    containerOverrides=ContainerOverridesTypeDef(
                        vcpus=container.cpu, memory=container.memory, command=container.command
                    ),
                    timeout=JobTimeoutTypeDef(attemptDurationSeconds=self.timeout),
                )
                job_id = submit_response["jobId"]

                # Poll for job completion
                task = asyncio.create_task(self.wait(layer=layer, job=job_id, batch=batch))
                return await asyncio.wait_for(task, timeout=self.timeout)
