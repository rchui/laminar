"""Local scheduler for laminar flows."""

import inspect
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from laminar import configs
from laminar.exceptions import ArtifactError
from laminar.schedulers.base import Scheduler

if TYPE_CHECKING:
    from laminar.components import Flow
else:
    Flow = Any

logger = configs.logger


class Local(Scheduler):
    def __call__(self, flow: Flow, **parameters: Any) -> None:
        """Execute the flow."""

        workspace = os.path.join(configs.workspace.path or str(Path.cwd().resolve() / ".laminar"), flow.name, flow.id)

        # Create the workspace folder
        logger.info("Workspace: %s", workspace)
        Path(workspace).resolve().mkdir(parents=True, exist_ok=True)

        # Store flow parameters in the workspace
        flow.store_artifacts(workspace, **parameters)

        for step in self.queue:
            logger.info("Starting step %s.", step.__name__)

            # Marshall step parameters from the workspace
            artifacts: Dict[str, Any] = {}
            for key in inspect.getfullargspec(step).args:
                try:
                    artifacts[key] = flow.load_artifact(workspace, key)
                except BaseException:
                    raise ArtifactError(
                        f"Error loading artifact '{key}' for step '{step.__name__}' in flow '{flow.name}' during"
                        + f"execution '{flow.id}'. Was it created in the flow?"
                    )
            # Exceute the step
            results = step(**artifacts)

            # For each result, store the artifacts in the workspace
            flow.store_artifacts(workspace, **results.dict())
            logger.info("Finishing step %s.", step.__name__)
