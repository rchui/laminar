"""Components for laminar flows."""

import functools
import inspect
import os
import pickle
from typing import Any, Callable, TypeVar, cast

import ulid
from pydantic import BaseModel as Response
from smart_open import open
from typeguard import typechecked

from laminar import configs
from laminar.schedulers import Local
from laminar.schedulers.base import Scheduler

F = TypeVar("F", bound=Callable[..., Response])

logger = configs.logger


class Flow:
    def __init__(self, *, name: str, project: str, scheduler: Scheduler = Local()) -> None:
        """A collection of laminar tasks.

        Args:
            name (str): Name of the flow.
            project (str): Project the flow belongs to.
        """

        self.name = name
        self.project = project

        self.scheduler = scheduler

        if isinstance(self.scheduler, Local):
            self.id = str(ulid.new())
        else:
            self.id = str(ulid.new())

    def __call__(self, **parameters: Any) -> None:
        """Execute the laminar flow using the configured scheduler."""

        self.scheduler(self, **parameters)

    def task(self, *sources: Callable[..., Response]) -> Callable[[F], F]:
        """Define a function as a step in a laminar flow."""

        def decorator(f: F) -> F:
            f = typechecked(f)  # type: ignore

            @functools.wraps(f)
            def wrapper(*args: Any, **kwargs: Any) -> Response:
                return f(*args, **kwargs)

            # Register steps and dependencies for executing flow dag.
            self.scheduler.register(wrapper)
            for source in sources:
                self.scheduler.add_dependency(source, wrapper)

            # Update the wrapper signature so that we can inspect the original argspec
            wrapper.__signature__ = inspect.signature(f)  # type: ignore
            # Cast back to original function so type resolution works correctly
            return cast(F, wrapper)

        return decorator

    def load_artifact(self: "Flow", workspace: str, key: str) -> Any:
        """For a given step, load the needed artifacts from the shared flow directory.

        Args:
            workspace (Path): Workspace that the execution's artifacts are stored.

        Returns:
            Any: The value artifact value for the given key.
        """

        logger.info("Loading artifact %s from workspace.", key)

        with open(os.path.join(workspace, f"{key}.gz"), "rb") as artifact:
            return pickle.loads(artifact.read())

    def store_artifacts(self: "Flow", workspace: str, **artifacts: Any) -> None:
        """For all values returned by a step, store each artifact in teh shared flow directory.

        Args:
            workspace (Path): Workspace that the execution's artifacts are stored.
        """

        logger.info("Storing artifacts %s in workspace.", ", ".join(artifacts.keys()))

        for key, value in artifacts.items():
            with open(os.path.join(workspace, f"{key}.gz"), "wb") as artifact:
                artifact.write(pickle.dumps(value))
