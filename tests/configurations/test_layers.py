"""Tests for laminar.configurations.layers"""

from typing import Any, Dict

import pytest

from laminar import Flow, Layer
from laminar.configurations.datastores import Archive, Artifact
from laminar.configurations.layers import ForEach, Parameter


class TestForEach:
    @pytest.fixture(autouse=True)
    def _flow(self, flow: Flow) -> None:
        workspace: Dict[str, Any] = flow.configuration.datastore.cache
        workspace["memory:///TestFlow/archives/test-execution/A/0/foo.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="1"), Artifact(dtype="str", hexdigest="2")]
        )
        workspace["memory:///TestFlow/archives/test-execution/B/0/bar.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="3"), Artifact(dtype="str", hexdigest="4")]
        )
        workspace["memory:///TestFlow/archives/test-execution/C/0/foo.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="a")]
        )
        workspace["memory:///TestFlow/archives/test-execution/C/1/foo.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="b")]
        )
        workspace["memory:///TestFlow/archives/test-execution/C/2/foo.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="c")]
        )
        workspace["memory:///TestFlow/archives/test-execution/C/3/foo.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="d")]
        )

        workspace["memory:///TestFlow/artifacts/1.gz"] = True
        workspace["memory:///TestFlow/artifacts/2.gz"] = False
        workspace["memory:///TestFlow/artifacts/3.gz"] = 0
        workspace["memory:///TestFlow/artifacts/4.gz"] = 1

        self.flow = flow

        @self.flow.register()
        class A(Layer):
            ...

        @self.flow.register()
        class B(Layer):
            ...

        @self.flow.register(
            foreach=ForEach(parameters=[Parameter(layer=A, attribute="foo"), Parameter(layer=B, attribute="bar")])
        )
        class C(Layer):
            ...

        self.A = A
        self.B = B
        self.C = C

    def test_join(self) -> None:
        layer = self.flow.layer(self.C)
        assert layer.configuration.foreach.join(layer=layer, name="foo") == Archive(
            artifacts=[
                Artifact(dtype="str", hexdigest="a"),
                Artifact(dtype="str", hexdigest="b"),
                Artifact(dtype="str", hexdigest="c"),
                Artifact(dtype="str", hexdigest="d"),
            ]
        )

    def test_grid(self) -> None:
        layer = self.flow.layer(self.C)
        assert layer.configuration.foreach.grid(layer=layer) == [
            {self.A(): {"foo": 0}, self.B(): {"bar": 0}},
            {self.A(): {"foo": 0}, self.B(): {"bar": 1}},
            {self.A(): {"foo": 1}, self.B(): {"bar": 0}},
            {self.A(): {"foo": 1}, self.B(): {"bar": 1}},
        ]

    def test_splits(self) -> None:
        layer = self.flow.layer(self.C)
        assert layer.configuration.foreach.splits(layer=layer) == 4

    def test_set(self) -> None:
        layer = self.flow.layer(self.C, index=0)
        A, B = layer.configuration.foreach.set(
            layer=layer, parameters=(self.flow.layer(self.A), self.flow.layer(self.B))
        )

        assert A.foo is True
        assert B.bar == 0

        layer = self.flow.layer(self.C, index=3)
        A, B = layer.configuration.foreach.set(
            layer=layer, parameters=(self.flow.layer(self.A), self.flow.layer(self.B))
        )

        assert A.foo is False
        assert B.bar == 1
