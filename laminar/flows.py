from laminar.exceptions import FlowError
from typing import Callable, Dict, Set, Type, TypeVar

from pydantic import BaseModel, create_model

from laminar.layers import Configuration, Layer, Container, Dependencies, Resources

__all__ = ["Flow"]

T = TypeVar("T")


class Flow(BaseModel):
    name: str
    _dag: Dict[Type[Layer], Set[Type[Layer]]] = {}
    _mapping: Dict[str, Type[Layer]] = {}

    @property
    def dag(self) -> Dict[str, str]:
        return {child.__name__: {parent.__name__ for parent in parents} for child, parents in self._dag.items()}

    def __call__(self) -> None:
        dag = self.dag
        finished: Set[str] = set()

        pending = {self._mapping[name] for name, parents in dag.items() if parents.issubset(finished)}

        while pending:
            for layer in pending:
                layer()()

                finished.add(layer.__name__)
                dag.pop(layer.__name__)

            pending = {self._mapping[name] for name, parents in dag.items() if parents.issubset(finished)}

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
        def wrapped(layer: T) -> T:
            layer = create_model(
                layer.__name__,
                __base__=layer,
                configuration=Configuration(container=container, dependencies=dependencies, resources=resources),
            )

            if layer.__name__ in self._mapping:
                raise FlowError(
                    f"The {layer.__name__} layer being added more than once to the {self.name} flow."
                )

            self._mapping[layer.__name__] = layer
            self._dag[layer] = set()
            for parent in dependencies.dependencies.values():
                self._dag[layer].add(parent)

            return layer

        return wrapped
