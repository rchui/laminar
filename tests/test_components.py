"""Tests for laminar.components"""

import copy

import cloudpickle
import pytest

from laminar import Flow, Layer
from laminar.configurations.datastores import Archive, Artifact
from laminar.exceptions import LayerError


class TestLayer:
    def test_init(self) -> None:
        assert vars(Layer()) == {}
        assert Layer(foo="bar").foo == "bar"

    def test_subclass_init(self) -> None:
        assert Layer().namespace is None

        class Test(Layer, namespace="foo"):
            ...

        assert Test().namespace == "foo"

    def test_subclass_init_alphanum(self) -> None:
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
            "memory:///TestFlow/test-execution/Layer/0/foo.json": Archive(
                artifacts=[
                    Artifact(hexdigest="112bda3b495d867b6a98c899fac7c25eb60ca4b6e6fe5ec7ab9299f93e8274bc"),
                    Artifact(hexdigest="24a5341c9a6e30357187cbeaebee0a02714ee3b3d6cead951a613e96ffb746dc"),
                    Artifact(hexdigest="9c298d589a2158eb513cb52191144518a2acab2cb0c04f1df14fca0f712fa4a1"),
                ]
            ),
            "memory:///artifacts/112bda3b495d867b6a98c899fac7c25eb60ca4b6e6fe5ec7ab9299f93e8274bc.gz": True,
            "memory:///artifacts/24a5341c9a6e30357187cbeaebee0a02714ee3b3d6cead951a613e96ffb746dc.gz": False,
            "memory:///artifacts/9c298d589a2158eb513cb52191144518a2acab2cb0c04f1df14fca0f712fa4a1.gz": None,
        }
