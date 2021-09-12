"""Laminar flow components."""

import abc
import logging
import os
import pickle
import shlex
import subprocess
import sys
from collections import defaultdict
from graphlib import TopologicalSorter
from typing import Any, Dict, List, Set, Tuple, Type, Union, cast

from ksuid import Ksuid
from pydantic import BaseModel
from smart_open import open

from laminar import configuration

logger = logging.getLogger(__name__)


class Step(BaseModel, abc.ABC):
    """Basic building block of a laminar flow."""

    class Config:
        extra = "forbid"

    class Container:
        image: str = f"python:{configuration.python.major}.{configuration.python.minor}"
        executable: str = "python"
        entrypoint: str = "main.py"

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)

    @abc.abstractmethod
    def __call__(self) -> None:
        ...


class Pipeline:
    def __init__(self, name: str, *steps: Union[Type[Step], List[Type[Step]]]) -> None:
        if name.isalpha():
            self.name = name
            self.title = "".join([part.capitalize() for part in self.name.split()])
        else:
            raise Exception

        self.start = self.step_factory(
            f"{self.title}Start", container=dict(executable="echo", entrypoint=f"Starting {name} pipeline...")
        )
        self.end = self.step_factory(
            f"{self.title}End", container=dict(executable="echo", entrypoint=f"Ending {name} pipeline...")
        )

        self._dag = self.build_dag(self.start, steps, self.end)

        # Get the toplogical sorted order
        self._order = tuple(TopologicalSorter(self._dag).static_order())

        if configuration.state.pipeline:
            self.execute_pipeline()

        elif configuration.state.step:
            self.execute_step(configuration.step.name)

    @property
    def dag(self) -> Dict[str, Set[str]]:
        return {child.__name__: {parent.__name__ for parent in parents} for child, parents in self._dag.items()}

    @property
    def order(self) -> Tuple[str, ...]:
        return tuple(step.__name__ for step in self._order)

    @property
    def name_to_step(self) -> Dict[str, Type[Step]]:
        return {step.__name__: step for step in self._order}

    def step_factory(self, name: str, *, container: Dict[str, Any]) -> Type[Step]:
        _container = type("Container", (Step.Container,), container)
        return cast(Type[Step], type(name, (Step,), dict(Container=_container)))

    def build_dag(
        self, start: Type[Step], steps: Tuple[Union[Type[Step], List[Type[Step]]], ...], end: Type[Step]
    ) -> Dict[Type[Step], Set[Type[Step]]]:
        # Reverse step order
        steps = steps[::-1]

        # Normalize steps to all be list of steps
        tasks = [step if isinstance(step, list) else [step] for step in steps]

        # Add start and ending steps
        tasks = [[end]] + tasks + [[start]]

        # Add all tasks to the dag
        dag: Dict[Type[Step], Set[Type[Step]]] = defaultdict(set)
        children = tasks[0]
        for parents in tasks[1:]:
            for child in children:
                for parent in parents:
                    dag[child].add(parent)
            children = parents

        return dag

    def execute_pipeline(self) -> None:
        execution_id = Ksuid()

        sorter = TopologicalSorter(self._dag)
        sorter.prepare()
        while sorter.is_active():
            for step in sorter.get_ready():
                command = " ".join(
                    (
                        "docker",
                        "run",
                        "--rm",
                        "--interactive",
                        "--tty",
                        "--env",
                        f"LAMINAR_EXECUTION_ID={execution_id}",
                        "--env",
                        f"LAMINAR_PIPELINE_NAME={self.name}",
                        "--env",
                        "LAMINAR_STATE_STEP=True",
                        "--env",
                        f"LAMINAR_STEP_NAME={step.__name__}",
                        "--volume",
                        f"{os.getcwd()}/.laminar:/laminar/.laminar",
                        getattr(step.Container, "image", Step.Container.image),
                        getattr(step.Container, "executable", Step.Container.executable),
                        getattr(step.Container, "entrypoint", Step.Container.entrypoint),
                    )
                )
                logger.debug(command)

                try:
                    subprocess.run(shlex.split(command), check=True)
                except subprocess.CalledProcessError as error:
                    logger.error("Unhandled error in step %s: %s", step.__name__, str(error))
                    sys.exit(1)

                sorter.done(step)

    def execute_step(self, name: str) -> None:
        logger.info("Starting step %s", name)

        step = self.name_to_step[name]

        directory = f"{configuration.artifact.source}/{configuration.pipeline.name}/{configuration.execution.id}"
        os.makedirs(directory, exist_ok=True)

        artifacts: Dict[str, Any] = {}
        for field, value in vars(step)["__fields__"].items():
            if value.required:
                with open(f"{directory}/{field}.gz", "rb") as artifact:
                    artifacts[field] = pickle.loads(artifact.read())

        run = step(**artifacts)
        run()

        for field in vars(run):
            with open(f"{directory}/{field}.gz", "wb") as artifact:
                artifact.write(pickle.dumps(getattr(run, field)))

        logger.info("Ending step %s", name)
