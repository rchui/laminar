import logging
from typing import Dict, Set, Type, TypeVar

from pydantic import BaseModel

from laminar.settings import current

__all__ = ["Layer", "Container", "Dependencies", "Resources"]
T = TypeVar("T")

logger = logging.getLogger(__name__)


class Container(BaseModel):
    command: str = "python main.py"
    image: str = f"python:{current.python.major}.{current.python.minor}"
    workdir: str = "/laminar"


class Dependencies(BaseModel):
    layers: Set[Type["Layer"]]
    data: Dict[str, Type["Layer"]]

    def __init__(__pydantic_self__, *layers: Type["Layer"], **data: Type["Layer"]) -> None:
        super().__init__(layers=set(layers), data=data)


class Resources(BaseModel):
    cpu: int
    memory: int

    def __init__(__pydantic_self__, *, cpu: int = 1, memory: int = 1500) -> None:
        super().__init__(cpu=cpu, memory=memory)


class Configuration(BaseModel):
    container: Container
    dependencies: Dependencies
    resources: Resources

    def __init__(
        __pydantic_self__,
        *,
        container: Container = Container(),
        dependencies: Dependencies = Dependencies(),
        resources: Resources = Resources(),
    ) -> None:
        super().__init__(container=container, dependencies=dependencies, resources=resources)


class Layer(BaseModel):
    configuration: Configuration

    def __init_subclass__(
        cls,
        container: Container = Container(),
        dependencies: Dependencies = Dependencies(),
        resources: Resources = Resources(),
    ) -> None:
        cls.configuration = Configuration(container=container, dependencies=dependencies, resources=resources)
        return super().__init_subclass__()

    def __call__(self) -> None:
        logger.info("Starting layer %s", self.__repr_name__())
