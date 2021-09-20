import logging
from typing import Dict, Type, TypeVar

from pydantic import BaseModel

__all__ = ["Layer", "Container", "Dependencies", "Resources"]
T = TypeVar("T")

logger = logging.getLogger(__name__)


class Container(BaseModel):
    image: str
    command: str

    def __init__(__pydantic_self__, *, image: str = "python:3.6", command: str = "python main.py") -> None:
        super().__init__(image=image, command=command)


class Dependencies(BaseModel):
    dependencies: Dict[str, Type["Layer"]]

    def __init__(__pydantic_self__, **dependencies: Type["Layer"]) -> None:
        super().__init__(dependencies=dependencies)


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
    configuration: Configuration = Configuration()

    def __call__(self) -> None:
        logger.info("Starting layer %s", self.__repr_name__())
