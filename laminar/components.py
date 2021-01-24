"""Components for laminar flows."""

import functools
import inspect
import os
import pickle
from pathlib import Path
from typing import Any, Callable, Dict, TypeVar, cast

import ulid
from smart_open import open, parse_uri
from typeguard import typechecked

from laminar import configs
from laminar.exceptions import ArtifactError
from laminar.schedulers import Scheduler
from laminar.types import Step

T = TypeVar("T", bound=Callable[..., Dict[str, Any]])


class Flow:
    def __init__(self: "Flow", name: str, scheduler: Scheduler) -> None:
        """A collection of laminar steps.

        Args:
            name (str): Name of the flow.
        scheduler (Scheduler): Scheduler to use to execute the flow.
        """

        self.name = name

        self.id = str(ulid.new())
        self.scheduler = scheduler

    def __call__(self: "Flow", **parameters: Any) -> None:
        """Execute the flow."""

        execution_workspace = os.path.join(
            configs.workspace.path or str(Path.cwd().resolve() / ".laminar"), self.name, self.id
        )

        # Create workspace folder
        if parse_uri(execution_workspace).scheme == "file":
            Path(execution_workspace).resolve().mkdir(parents=True, exist_ok=True)

        # Store flow parameters
        self.write_artifacts(execution_workspace, **parameters)

        for step in self.scheduler.queue:
            # For each arg in the step, fetch the stored arg from a previous
            key: str = None

            try:
                # Marshall step parameters
                artifacts = self.read_artifacts(execution_workspace, *inspect.getfullargspec(step).args)
            except FileNotFoundError:
                raise ArtifactError(
                    f"Error loading artifact '{key}' for step '{step.__name__}' in flow '{self.name}' during execution"
                    + f" '{self.id}'. Was it created in the flow?"
                )
            # Exceute the step
            results = step(**artifacts)

            # For each result, store the artifacts in the shared flow directory.
            self.write_artifacts(execution_workspace, **results)

    def read_artifacts(self: "Flow", execution_workspace: str, *args: str) -> Dict[str, Any]:
        """For a given step, load the needed artifacts from the shared flow directory.

        Args:
            execution_workspace (Path): Workspace that the execution's artifacts are stored.

        Returns:
            Dict[str, Any]: Artifact names mapped to values.
        """

        artifacts: Dict[str, Any] = {}
        for key in args:
            with open(os.path.join(execution_workspace, f"{key}.gz"), "rb") as artifact:
                artifacts[key] = pickle.loads(artifact.read())

        return artifacts

    def write_artifacts(self: "Flow", execution_workspace: str, **arifacts: Any) -> None:
        """For all values returned by a step, store each artifact in teh shared flow directory.

        Args:
            execution_workspace (Path): Workspace that the execution's artifacts are stored.
        """

        for key, value in arifacts.items():
            with open(os.path.join(execution_workspace, f"{key}.gz"), "wb") as artifact:
                artifact.write(pickle.dumps(value))

    def step(self: "Flow", *next: Step) -> Callable[[T], T]:
        """Define a function as a step in a laminar flow.

        Args:
            next (Optional[Iterable[Step]], optional): List of steps to execute after this one. Defaults to None.
        """

        def decorator(f: Step) -> T:
            f = typechecked(f)

            @functools.wraps(f)
            def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
                return f(*args, **kwargs)

            # Register steps and dependencies for executing flow dag.
            self.scheduler.register(wrapper)
            for step in next:
                self.scheduler.add_dependency(wrapper, step)

            # Update the wrapper signature so that we can inspect the original argspec
            wrapper.__signature__ = inspect.signature(f)  # type: ignore
            # Cast back to original function so type resolution works correctly
            return cast(T, wrapper)

        return decorator

    def submit(self: "Flow") -> None:
        self.scheduler.submit(self)
