"""Tests for laminar.components"""

import copy
from typing import Any, Dict
from unittest.mock import ANY, Mock, patch

import cloudpickle
import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores
from laminar.exceptions import FlowError, LayerError
from laminar.settings import current
from laminar.utils import contexts


class TestLayer:
    def test_init(self) -> None:
        assert vars(Layer()) == {}
        assert Layer(foo="bar").foo == "bar"

    def test_subclass_init(self) -> None:
        assert Layer().namespace is None

        class Test(Layer, namespace="foo"):
            ...

        assert Test().namespace == "foo"

        with pytest.raises(LayerError):

            class _(Layer, namespace="test-namespace"):
                ...

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
        assert vars(cloudpickle.loads(cloudpickle.dumps(Layer(foo="bar")))) == {"foo": "bar"}

    def test_name(self) -> None:
        assert Layer().name == "Layer"

        class Subclass(Layer):
            ...

        assert Subclass().name == "Subclass"

        class Namespace(Layer, namespace="Test"):
            ...

        assert Namespace().name == "Test.Namespace"

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

        assert flow.layer(Test).dependencies == ("Dep1", "Dep2")

    def test_getattr(self, flow: Flow) -> None:
        workspace: Dict[str, Any] = flow.configuration.datastore.cache
        workspace["memory:///TestFlow/archives/test-execution/Layer/0/foo.json"] = datastores.Archive(
            artifacts=[datastores.Artifact(hexdigest="abc")]
        )
        workspace["memory:///TestFlow/archives/test-execution/Layer/0/bar.json"] = datastores.Archive(
            artifacts=[datastores.Artifact(hexdigest="123"), datastores.Artifact(hexdigest="456")]
        )

        workspace["memory:///TestFlow/artifacts/abc.gz"] = True

        flow.register()(Layer)

        assert flow.layer(Layer, index=0).foo is True
        assert flow.layer(Layer, index=0).bar == datastores.Accessor(
            archive=datastores.Archive(
                artifacts=[datastores.Artifact(hexdigest="123"), datastores.Artifact(hexdigest="456")]
            ),
            layer=Layer(),
        )

    def test_shard(self, flow: Flow) -> None:
        flow.register()(Layer)
        flow.layer(Layer, index=0).shard(foo=[True, False, None])

        assert flow.configuration.datastore.cache == {
            "memory:///TestFlow/archives/test-execution/Layer/0/foo.json": datastores.Archive(
                artifacts=[
                    datastores.Artifact(hexdigest="5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae"),
                    datastores.Artifact(hexdigest="132915fa0f4abd3a7939610b8d088fbbcdff866e17b5cbb2c0bdcb37782f4da2"),
                    datastores.Artifact(hexdigest="6c09635decb8153d3c12e3782a69fd2eb097426f912547d351a8647b27d5580a"),
                ]
            ),
            "memory:///TestFlow/artifacts/5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae.gz": True,
            "memory:///TestFlow/artifacts/132915fa0f4abd3a7939610b8d088fbbcdff866e17b5cbb2c0bdcb37782f4da2.gz": False,
            "memory:///TestFlow/artifacts/6c09635decb8153d3c12e3782a69fd2eb097426f912547d351a8647b27d5580a.gz": None,
        }


class TestFLow:
    def test_init(self) -> None:
        with pytest.raises(FlowError):
            Flow(name="test-name")

        with pytest.raises(FlowError):
            Flow(name="TestFlow", datastore=datastores.Memory())

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

        assert flow.dependencies == {"Dep1": (), "Dep2": (), "Test": ("Dep1", "Dep2")}
        assert flow.dependents == {"Dep1": {"Test"}, "Dep2": {"Test"}}

    @patch("laminar.components.Flow.schedule")
    @patch("laminar.components.Flow.execute")
    def test_call(self, mock_execute: Mock, mock_schedule: Mock, flow: Flow) -> None:
        with contexts.Attributes(flow, execution=None):
            flow()

        mock_schedule.assert_called_once_with(dependencies={}, execution=ANY)

        @flow.register()
        class Test(Layer):
            ...

        with contexts.Attributes(current.layer, name="Test"), contexts.Attributes(current.flow, name="TestFlow"):
            flow()
        assert mock_execute.call_args[-1]["layer"] == Test()

    def test_execute(self) -> None:
        ...

    def test_schedule(self) -> None:
        ...

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
        assert flow.dependencies == {"Dep1": (), "Dep2": (), "Test": ("Dep1", "Dep2")}
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
