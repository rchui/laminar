import logging
import os
import shlex
import subprocess
from pathlib import Path
from laminar.exceptions import FlowError
from typing import Any, Callable, Dict, Set, Type, TypeVar

import cloudpickle
from ksuid import Ksuid
from smart_open import open
from pydantic import BaseModel, create_model

from laminar.settings import current
from laminar.layers import Configuration, Layer, Container, Dependencies, Resources

__all__ = ["DataSource", "Flow"]

T = TypeVar("T")

logger = logging.getLogger(__name__)


class DataSource(BaseModel):
    root: str

    def __init__(__pydantic_self__, root: str = ".laminar") -> None:
        super().__init__(root=root)

    def uri(self, flow: str, id: str, step: str) -> str:
        return f"{self.root}/{flow}/{id}/{step}"

    def read(self, uri: str, artifact: str) -> Any:
        with open(f"{uri}/{artifact}.gz", "rb") as archive:
            return cloudpickle.load(archive)

    def write(self, uri: str, artifact: str, value: Any) -> None:
        Path(uri).mkdir(parents=True, exist_ok=True)
        with open(f"{uri}/{artifact}.gz", "wb") as archive:
            cloudpickle.dump(value, archive)


class Flow(BaseModel):
    datasource: DataSource
    id: str
    _dag: Dict[Type[Layer], Set[Type[Layer]]] = {}
    _mapping: Dict[str, Type[Layer]] = {}

    def __init__(__pydantic_self__, datasource: DataSource = DataSource()) -> None:
        super().__init__(datasource=datasource, id=current.execution.id or str(Ksuid()))

    @property
    def dag(self) -> Dict[str, str]:
        return {child.__name__: {parent.__name__ for parent in parents} for child, parents in self._dag.items()}

    @property
    def name(self) -> str:
        return self.__repr_name__()

    def __call__(self) -> None:
        def get_pending(dag: Dict[str, str], finished: Set[str]) -> Set[Type[Layer]]:
            return {self._mapping[name] for name, parents in dag.items() if parents.issubset(finished)}

        if current.layer.name is not None:
            layer = self._mapping[current.layer.name]

            configuration: Configuration = layer.__fields__["configuration"].default

            parameters = {
                artifact: self.datasource.read(self.datasource.uri(self.name, self.id, source.__name__), artifact)
                for artifact, source in configuration.dependencies.data.items()
            }

            run = layer(**parameters)

            run()

            for artifact, value in vars(run).items():
                if artifact != "configuration":
                    self.datasource.write(self.datasource.uri(self.name, self.id, layer.__name__), artifact, value)

        else:
            dag = self.dag
            finished: Set[str] = set()

            pending = get_pending(dag, finished)

            while pending:
                for layer in pending:
                    configuration: Configuration = layer.__fields__["configuration"].default

                    archive = (
                        f"{os.getcwd()}/{self.datasource.root}:{configuration.container.workdir}/{self.datasource.root}"
                    )
                    command = " ".join(
                        [
                            "docker",
                            "run",
                            "--rm",
                            "--interactive",
                            "--tty",
                            f"--env LAMINAR_EXECUTION_ID={self.id}",
                            f"--env LAMINAR_LAYER_NAME={layer.__name__}",
                            f"--volume {archive}",
                            f"--workdir {configuration.container.workdir}",
                            configuration.container.image,
                            configuration.container.command,
                        ]
                    )
                    logger.info(command)
                    subprocess.run(shlex.split(command), check=True)

                    finished.add(layer.__name__)
                    dag.pop(layer.__name__)

                pending = get_pending(dag, finished)

                if not pending and dag:
                    raise FlowError(
                        f"A dependency exists for a step that is not registered with the {self.name} flow. "
                        f"Finished steps: {sorted(finished)}. "
                        f"Remaining dag: {dag}."
                    )

    def layer(
        self,
        *,
        container: Container = Container(),
        dependencies: Dependencies = Dependencies(),
        resources: Resources = Resources(),
    ) -> Callable[[T], T]:
        def wrapper(layer: T) -> T:
            layer = create_model(
                layer.__name__,
                __base__=layer,
                configuration=Configuration(container=container, dependencies=dependencies, resources=resources),
            )

            if layer.__name__ in self._mapping:
                raise FlowError(f"The {layer.__name__} layer is being added more than once to the {self.name} flow.")

            self._mapping[layer.__name__] = layer
            self._dag[layer] = {*dependencies.layers, *dependencies.data.values()}

            return layer

        return wrapper
