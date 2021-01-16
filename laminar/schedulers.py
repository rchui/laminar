"""Scheduler for laminar flows."""

from collections import defaultdict
from itertools import chain
from typing import Dict, Iterable, List, Set, TYPE_CHECKING

import boto3
from toposort import toposort

from laminar.types import Step

if TYPE_CHECKING:
    from .components import Flow
else:
    Flow = None


class Scheduler:
    def __init__(self, job_queue: str):
        self.job_queue = job_queue

    graph: Dict[str, Set[str]] = defaultdict(set)
    registry: Dict[str, Step] = {}

    def add_dependency(self, source: Step, destination: Step) -> None:
        """Add a dependency from a source step to a destination step.

        Args:
            source (Step): Step the dependency is starting from.
            destination (Step): Step the dependency is ending at.
        """

        self.graph[destination.__name__].add(source.__name__)

    def register(self, step: Step) -> None:
        """Register a function's name to the function.

        Args:
            step (Step): Step to register.
        """

        self.registry[step.__name__] = step

    @property
    def queue(self) -> Iterable[Step]:
        """Get topological sort of flow step dag."""

        for step in chain.from_iterable(toposort(self.graph)):
            yield self.registry[step]

    def submit(self, flow: Flow) -> None:
        """Submit a flow jobs to AWS Batch.

        Args:
            flow (Any): Flow's jobs that are getting submitted.
        """

        batch = boto3.client("batch")

        # Registe ra new job definition for the flow
        response = batch.register_job_definition(
            jobDefinitionName=f"laminar-{flow.name}",
            type="container",
            containerProperties=dict(image=..., jobRoleArn=..., executionRoleArn=...),
        )
        print(response)

        job_definition_arn = response["jobDefinitionArn"]

        # Submit each step as an AWS Batch Job
        dependencies: Dict[str, str] = {}
        for step in self.queue:

            # Enumerate all steps that this step should depnd on.
            depends_on: List[Dict[str, str]] = []
            if step.__name__ in self.graph:
                depends_on.extend([{"jobId": dependencies[dependency]} for dependency in self.graph[step.__name__]])

            response = batch.submit_job(
                jobName=f"laminar-{flow.name}-{flow.id}-{step.__name__}",
                jobQueue=self.job_queue,
                jobDefinition=job_definition_arn,
                depends_on=depends_on,
            )

            print(response)
            dependencies[step.__name__] = response["jobId"]
