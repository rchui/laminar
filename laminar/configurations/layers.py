"""Configurations for laminar layers."""

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Type, Union

from dacite.core import from_dict

if TYPE_CHECKING:
    from laminar.components import Layer
else:
    Layer = "Layer"


@dataclass(frozen=True)
class Container:
    command: str = "python main.py"
    cpu: int = 1
    image: str = "python:3.9"
    memory: int = 1500
    workdir: str = "/laminar"


@dataclass(frozen=True)
class Parameter:
    cls: Type["Layer"]
    attribute: str


@dataclass(frozen=True)
class ForEach:
    parameters: List[Parameter] = field(default_factory=list)


@dataclass(frozen=True)
class Configuration:
    container: Container = Container()
    foreach: ForEach = ForEach()

    def __or__(self, other: Union[Container, ForEach]) -> "Configuration":
        if isinstance(other, Container):
            new: Dict[str, Any] = {"container": other}
        elif isinstance(other, ForEach):
            new = {"foreach": other}
        else:
            raise NotImplementedError

        return from_dict(Configuration, {**asdict(self), **new})
