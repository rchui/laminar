"""Tests for laminar.components"""

import copy
from typing import Any, Dict
from unittest.mock import MagicMock

import cloudpickle
import pytest

from laminar import Flow, Layer
from laminar.configurations import layers
from laminar.configurations.datastores import Accessor, Archive, Artifact, Memory
from laminar.exceptions import FlowError
from laminar.utils import contexts


class TestLayer:
    def test_init(self) -> None:
        layer = Layer()
        assert vars(layer) == {}
        layer = Layer(foo="bar")
        assert vars(layer) == {"foo": "bar"}
        assert Layer(foo="bar").foo == "bar"

    def test_repr(self, layer: Layer) -> None:
        assert (
            repr(layer)
            == "Layer(flow=TestFlow(execution=Execution(id='test-execution', retry=False)), index=0, splits=2)"
        )

    def test_deepcopy(self) -> None:
        copy.deepcopy(Layer(foo="bar"))

    def test_equality(self) -> None:
        assert Layer() == "Layer"
        assert Layer() == Layer()

        class Test(Layer):
            ...

        assert Layer() != Test()
        assert Layer() != 0

    def test_pickle(self) -> None:
        layer = Layer(foo="bar")
        assert vars(cloudpickle.loads(cloudpickle.dumps(layer))) == {"foo": "bar"}

    def test_name(self) -> None:
        assert Layer().name == "Layer"

        class Subclass(Layer):
            ...

        assert Subclass().name == "Subclass"

    def test_state(self) -> None:
        layer = Layer()
        assert layer.state == layers.State(layer=layer)

    def test_dependencies(self, flow: Flow) -> None:
        @flow.register()
        class Dep1(Layer):
            ...

        @flow.register()
        class Dep2(Layer):
            ...

        @flow.register()
        class Test(Layer):
            def __call__(self, dep1: Dep1, dep2: Dep2) -> None:
                ...

        assert flow.layer(Test).dependencies == {"Dep1", "Dep2"}

    def test__dependencies(self, flow: Flow) -> None:
        @flow.register()
        class Dep1(Layer):
            ...

        @flow.register()
        class Dep2(Layer):
            ...

        @flow.register()
        class Test(Layer):
            def __call__(self, dep1: Dep1, dep2: Dep2) -> None:
                ...

        assert flow.layer(Test)._dependencies == {Dep1(), Dep2()}

    def test_getattr(self, flow: Flow) -> None:
        workspace: Dict[str, Any] = flow.configuration.datastore.cache
        workspace["memory:///TestFlow/archives/test-execution/Layer/0/foo.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="abc")]
        )
        workspace["memory:///TestFlow/archives/test-execution/Layer/0/bar.json"] = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="123"), Artifact(dtype="str", hexdigest="456")]
        )

        workspace["memory:///TestFlow/artifacts/abc.gz"] = True

        flow.register()(Layer)

        assert flow.layer(Layer, index=0).foo is True
        assert flow.layer(Layer, index=0).bar == Accessor(
            archive=Archive(artifacts=[Artifact(dtype="str", hexdigest="123"), Artifact(dtype="str", hexdigest="456")]),
            layer=Layer(),
        )

    def test_shard(self, flow: Flow) -> None:
        flow.register()(Layer)
        flow.layer(Layer, index=0).shard(foo=[True, False, None])

        assert flow.configuration.datastore.cache == {
            "memory:///TestFlow/artifacts/5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae.gz": True,
            "memory:///TestFlow/artifacts/132915fa0f4abd3a7939610b8d088fbbcdff866e17b5cbb2c0bdcb37782f4da2.gz": False,
            "memory:///TestFlow/artifacts/6c09635decb8153d3c12e3782a69fd2eb097426f912547d351a8647b27d5580a.gz": None,
            "memory:///TestFlow/archives/test-execution/Layer/0/foo.json": Archive(
                artifacts=[
                    Artifact(
                        dtype="builtins.bool",
                        hexdigest="5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae",
                    ),
                    Artifact(
                        dtype="builtins.bool",
                        hexdigest="132915fa0f4abd3a7939610b8d088fbbcdff866e17b5cbb2c0bdcb37782f4da2",
                    ),
                    Artifact(
                        dtype="builtins.NoneType",
                        hexdigest="6c09635decb8153d3c12e3782a69fd2eb097426f912547d351a8647b27d5580a",
                    ),
                ]
            ),
        }


class TestFLow:
    def test_init(self) -> None:
        with pytest.raises(FlowError):

            class InitFlow(Flow):
                ...

            InitFlow(datastore=Memory())

    def test_dependencies(self, flow: Flow) -> None:
        @flow.register()
        class Dep1(Layer):
            ...

        @flow.register()
        class Dep2(Layer):
            ...

        @flow.register()
        class Test(Layer):
            def __call__(self, dep1: Dep1, dep2: Dep2) -> None:
                ...

        assert flow.dependencies == {"Dep1": set(), "Dep2": set(), "Parameters": set(), "Test": {"Dep1", "Dep2"}}
        assert flow.dependents == {"Dep1": {"Test"}, "Dep2": {"Test"}}

    def test_call_schedule(self, flow: Flow) -> None:
        mock_execution = MagicMock()
        mock_execution.id = None

        flow.execution = mock_execution

        flow()

        mock_execution.return_value.parameters.return_value.schedule.assert_called_once_with(
            dependencies={"Parameters": set()}
        )

    def test_call_execute(self, flow: Flow) -> None:
        mock_execution = MagicMock()
        mock_execution.id = "test-execution"

        flow.execution = mock_execution

        @flow.register()
        class Test(Layer):
            ...

        flow()

        with contexts.Environment(LAMINAR_LAYER_NAME="Test", LAMINAR_FLOW_NAME="TestFlow"):
            flow()

        mock_execution.execute.assert_called_once_with(layer=Test())

    def test_register(self, flow: Flow) -> None:
        @flow.register()
        class Dep1(Layer):
            ...

        @flow.register()
        class Dep2(Layer):
            ...

        @flow.register()
        class Test(Layer):
            def __call__(self, dep1: Dep1, dep2: Dep2) -> None:
                ...

        assert {"Dep1": Dep1(), "Dep2": Dep2(), "Test": Test()}
        assert flow.dependencies == {"Dep1": set(), "Dep2": set(), "Parameters": set(), "Test": {"Dep1", "Dep2"}}
        assert flow.dependents == {"Dep1": {"Test"}, "Dep2": {"Test"}}

    def test_layer_duplicate(self, flow: Flow) -> None:
        @flow.register()
        class Test(Layer):
            ...

        with pytest.raises(FlowError):

            @flow.register()
            class Test(Layer):  # type: ignore # noqa
                ...

    def test_layer(self, flow: Flow) -> None:
        @flow.register()
        class Test(Layer):
            ...

        assert flow.layer("Test"), Test()
        assert flow.layer(Test), Test()
        assert flow.layer(Test()), Test()
        assert flow.layer(Test, foo="bar").foo == "bar"

    def test_results(self, flow: Flow) -> None:
        assert flow.execution("test-execution").id == "test-execution"
