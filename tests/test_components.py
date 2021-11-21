"""Tests for laminar.components"""

import copy
from unittest.mock import ANY, Mock, patch

import cloudpickle
import pytest

from laminar import Flow, Layer, contexts
from laminar.configurations import datastores
from laminar.exceptions import FlowError, LayerError
from laminar.settings import current


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
        @flow.layer()
        class Dep1(Layer):
            ...

        @flow.layer()
        class Dep2(Layer):
            ...

        @flow.layer()
        class Test(Layer):
            def __call__(self, dep1: Dep1, dep2: Dep2) -> None:  # type: ignore
                ...

        assert flow.get_layer(name=Test().name).dependencies == ("Dep1", "Dep2")

    def test_shard(self, flow: Flow) -> None:
        flow.layer()(Layer)
        flow.get_layer(name=Layer().name, index=0).shard(foo=[True, False, None])

        assert flow.configuration.datastore.workspace == {  # type: ignore
            "memory:///TestFlow/test-execution/Layer/0/foo.json": datastores.Archive(
                artifacts=[
                    datastores.Artifact(hexdigest="112bda3b495d867b6a98c899fac7c25eb60ca4b6e6fe5ec7ab9299f93e8274bc"),
                    datastores.Artifact(hexdigest="24a5341c9a6e30357187cbeaebee0a02714ee3b3d6cead951a613e96ffb746dc"),
                    datastores.Artifact(hexdigest="9c298d589a2158eb513cb52191144518a2acab2cb0c04f1df14fca0f712fa4a1"),
                ]
            ),
            "memory:///artifacts/112bda3b495d867b6a98c899fac7c25eb60ca4b6e6fe5ec7ab9299f93e8274bc.gz": True,
            "memory:///artifacts/24a5341c9a6e30357187cbeaebee0a02714ee3b3d6cead951a613e96ffb746dc.gz": False,
            "memory:///artifacts/9c298d589a2158eb513cb52191144518a2acab2cb0c04f1df14fca0f712fa4a1.gz": None,
        }


class TestFLow:
    def test_init(self) -> None:
        with pytest.raises(FlowError):
            Flow(name="test-name")

        with pytest.raises(FlowError):
            Flow(name="TestFlow", datastore=datastores.Memory())

    def test_dependencies(self, flow: Flow) -> None:
        @flow.layer()
        class Dep1(Layer):
            ...

        @flow.layer()
        class Dep2(Layer):
            ...

        @flow.layer()
        class Test(Layer):
            def __call__(self, dep1: Dep1, dep2: Dep2) -> None:  # type: ignore
                ...

        assert flow.dependencies == {"Dep1": (), "Dep2": (), "Test": ("Dep1", "Dep2")}
        assert flow.dependents == {"Dep1": {"Test"}, "Dep2": {"Test"}}

    @patch("laminar.components.Flow.schedule")
    @patch("laminar.components.Flow.execute")
    def test_call(self, mock_execute: Mock, mock_schedule: Mock, flow: Flow) -> None:
        flow()

        mock_schedule.assert_called_once_with(dependencies={}, execution=ANY)

        @flow.layer()
        class Test(Layer):
            ...

        with contexts.Attributes(current.layer, name="Test"), contexts.Attributes(flow, execution="test-execution"):
            flow()

            assert isinstance(mock_execute.call_args[-1]["layer"], Test)

    def test_execute(self) -> None:
        ...

    def test_schedule(self) -> None:
        ...

    def test_layer(self, flow: Flow) -> None:
        @flow.layer()
        class Dep1(Layer):
            ...

        @flow.layer()
        class Dep2(Layer):
            ...

        @flow.layer()
        class Test(Layer):
            def __call__(self, dep1: Dep1, dep2: Dep2) -> None:  # type: ignore
                ...

        for name, dtype in {"Dep1": Dep1, "Dep2": Dep2, "Test": Test}.items():
            assert name in flow._registry
            assert isinstance(flow._registry[name], dtype)
        assert flow.dependencies == {"Dep1": (), "Dep2": (), "Test": ("Dep1", "Dep2")}
        assert flow.dependents == {"Dep1": {"Test"}, "Dep2": {"Test"}}

    def test_layer_duplicate(self, flow: Flow) -> None:
        @flow.layer()
        class Test(Layer):
            ...

        with pytest.raises(FlowError):

            @flow.layer()  # noqa
            class Test(Layer):  # type: ignore
                ...

    def test_get_layer(self, flow: Flow) -> None:
        @flow.layer()
        class Test(Layer):
            ...

        assert isinstance(flow.get_layer(name=Test().name), Test)
        assert flow.get_layer(name=Test().name, foo="bar").foo == "bar"
