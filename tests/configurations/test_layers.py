"""Tests for laminar.configurations.layers"""

from typing import Any

import pytest

from laminar import Flow, Layer
from laminar.configurations.datastores import Archive, Artifact, Record
from laminar.configurations.layers import Catch, ForEach, Parameter


class TestCatch:
    def test_success(self) -> None:
        class A(Layer):
            def __call__(self) -> None:
                raise RuntimeError

        class B(Layer):
            def __call__(self) -> None:
                raise AssertionError

        catch = Catch(RuntimeError, AssertionError)

        class TestFlow(Flow): ...

        TestFlow.register(catch=catch)(A)
        TestFlow.register(catch=catch)(B)
        execution = TestFlow().execution("test")
        execution.layer(A).execute()
        execution.layer(B).execute()

    def test_failure(self) -> None:
        class A(Layer):
            def __call__(self) -> None:
                raise RuntimeError

        class TestFlow(Flow): ...

        TestFlow.register(A)
        with pytest.raises(RuntimeError):
            TestFlow().execution("test").layer(A).execute()

    def test_suberror(self) -> None:
        class A(Layer):
            def __call__(self) -> None:
                raise RuntimeError

        class TestFlow(Flow): ...

        TestFlow.register(catch=Catch(Exception))(A)
        TestFlow().execution("test").layer(A).execute()


class TestForEach:
    @pytest.fixture(autouse=True)
    def _flow(self, flow: Flow) -> None:
        workspace: dict[str, Any] = flow.configuration.datastore.cache
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
        self.execution = flow.test_execution

        @self.flow.register
        class A(Layer): ...

        @self.flow.register
        class B(Layer): ...

        @self.flow.register(
            foreach=ForEach(parameters=[Parameter(layer=A, attribute="foo"), Parameter(layer=B, attribute="bar")])
        )
        class C(Layer): ...

        @self.flow.register(foreach=ForEach(parameters=[Parameter(layer=C, attribute="foo", index=None)]))
        class D(Layer): ...

        self.A = A
        self.B = B
        self.C = C
        self.D = D

    def test_join(self) -> None:
        layer = self.execution.layer(self.C)
        assert layer.configuration.foreach.join(layer=layer, name="foo") == Archive(
            artifacts=[
                Artifact(dtype="str", hexdigest="a"),
                Artifact(dtype="str", hexdigest="b"),
                Artifact(dtype="str", hexdigest="c"),
                Artifact(dtype="str", hexdigest="d"),
            ]
        )

    def test_grid(self) -> None:
        layer = self.execution.layer(self.C)
        assert layer.configuration.foreach.grid(layer=layer) == [
            {self.A(): {"foo": 0}, self.B(): {"bar": 0}},
            {self.A(): {"foo": 0}, self.B(): {"bar": 1}},
            {self.A(): {"foo": 1}, self.B(): {"bar": 0}},
            {self.A(): {"foo": 1}, self.B(): {"bar": 1}},
        ]

    def test_grid_none(self) -> None:
        layer = self.execution.layer(self.D)
        assert layer.configuration.foreach.grid(layer=layer) == [
            {self.C(): {"foo": 0}},
            {self.C(): {"foo": 1}},
            {self.C(): {"foo": 2}},
            {self.C(): {"foo": 3}},
        ]

    def test_splits(self) -> None:
        layer = self.execution.layer(self.C)
        assert layer.configuration.foreach.splits(layer=layer) == 4

    def test_splits_cache_hit(self) -> None:
        self.flow.configuration.datastore.cache["memory:///TestFlow/.cache/test-execution/C/.record.json"] = Record(
            flow=Record.FlowRecord("Testflow"),
            layer=Record.LayerRecord(name="C"),
            execution=Record.ExecutionRecord(splits=6),
        )

        layer = self.execution.layer(self.C)
        assert layer.configuration.foreach.splits(layer=layer) == 6

    def test_set(self) -> None:
        print(self.flow)
        print(self.flow.execution)
        layer = self.execution.layer(self.C, index=0)

        print(layer)

        A, B = layer.configuration.foreach.set(
            layer=layer, parameters=(self.execution.layer(self.A), self.execution.layer(self.B))
        )

        assert A.foo is True
        assert B.bar == 0

        layer = self.execution.layer(self.C, index=3)
        A, B = layer.configuration.foreach.set(
            layer=layer, parameters=(self.execution.layer(self.A), self.execution.layer(self.B))
        )

        assert A.foo is False
        assert B.bar == 1
