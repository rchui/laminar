"""Abstract base class for laminar flow schedulers."""

from abc import ABC, abstractmethod
from collections import defaultdict
from itertools import chain
from typing import TYPE_CHECKING, Any, Dict, Iterable, Set

from toposort import toposort

from laminar.types import Step

if TYPE_CHECKING:
    from laminar.components import Flow
else:
    Flow = Any


class Scheduler(ABC):
    graph: Dict[str, Set[str]] = defaultdict(set)
    registry: Dict[str, Step] = {}

    @abstractmethod
    def __call__(self, flow: Flow, **parameters: Any) -> None:
        ...

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
