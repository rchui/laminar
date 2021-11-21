"""Tests for laminar.configurations.datastores"""

from typing import Any, Dict

import pytest

from laminar import Flow, Layer
from laminar.configurations import datastores, executors


@pytest.fixture()
def flow() -> Flow:
    flow = Flow(name="TestFlow", datastore=datastores.Memory(), executor=executors.Thread())
    flow.execution = "test-execution"
    return flow


@pytest.fixture()
def layer(flow: Flow) -> Layer:
    return Layer(flow=flow, index=0)


class TestArtifact:
    artifact = datastores.Artifact(hexdigest="foo")

    def test_dict(self) -> None:
        assert self.artifact.dict() == {"hexdigest": "foo"}

    def test_path(self) -> None:
        assert self.artifact.path() == "artifacts/foo.gz"


class TestArchive:
    archive = datastores.Archive(artifacts=[datastores.Artifact(hexdigest="foo"), datastores.Artifact(hexdigest="bar")])

    def test_dict(self) -> None:
        assert self.archive.dict() == {"artifacts": [{"hexdigest": "foo"}, {"hexdigest": "bar"}]}

    def test_len(self) -> None:
        assert len(self.archive) == 2

    def test_path(self, layer: Layer) -> None:
        assert (
            self.archive.path(layer=layer, index=0, name="test-archive")
            == f"{layer.flow.name}/{layer.flow.execution}/{layer.name}/{layer.index}/test-archive.json"
        )

    def test_parse(self) -> None:
        expected = {"artifacts": [{"hexdigest": "foo"}, {"hexdigest": "bar"}]}
        assert datastores.Archive.parse(expected).dict() == expected


class TestAccessor:
    @pytest.fixture(autouse=True)
    def _accessor(self, layer: Layer) -> None:
        workspace: Dict[str, Any] = layer.flow.configuration.datastore.workspace  # type: ignore
        workspace["memory:/artifacts/test-hexdigest-0.gz"] = "foo"
        workspace["memory:/artifacts/test-hexdigest-1.gz"] = "bar"

        self.accessor = datastores.Accessor(
            archive=datastores.Archive(
                artifacts=[
                    datastores.Artifact(hexdigest="test-hexdigest-0"),
                    datastores.Artifact(hexdigest="test-hexdigest-1"),
                ]
            ),
            layer=layer,
        )

    def test_len(self) -> None:
        assert len(self.accessor) == 2

    def test_get_item(self) -> None:
        assert [self.accessor[0], self.accessor[1]] == ["foo", "bar"]

    def test_iterable(self) -> None:
        assert list(self.accessor) == ["foo", "bar"]

    def test_slice(self) -> None:
        assert self.accessor[:1] == ["foo"]
