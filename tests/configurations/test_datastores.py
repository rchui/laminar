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


def test_artifact() -> None:
    artifact = datastores.Artifact(hexdigest="foo")

    assert artifact.dict() == {"hexdigest": "foo"}
    assert artifact.path() == "artifacts/foo.gz"


def test_archive(layer: Layer) -> None:
    archive = datastores.Archive(artifacts=[datastores.Artifact(hexdigest="foo"), datastores.Artifact(hexdigest="bar")])

    assert archive.dict() == {"artifacts": [{"hexdigest": "foo"}, {"hexdigest": "bar"}]}
    assert len(archive) == 2
    assert (
        datastores.Archive(artifacts=[datastores.Artifact(hexdigest="foo")]).path(
            layer=layer, index=0, name="test-archive"
        )
        == f"{layer.flow.name}/{layer.flow.execution}/{layer.name}/{layer.index}/test-archive.json"
    )


def test_archive_parse() -> None:
    expected = {"artifacts": [{"hexdigest": "foo"}, {"hexdigest": "bar"}]}
    assert datastores.Archive.parse(expected).dict() == expected


def test_accessor(layer: Layer) -> None:
    workspace: Dict[str, Any] = layer.flow.configuration.datastore.workspace  # type: ignore
    workspace["memory:/artifacts/test-hexdigest-0.gz"] = "foo"
    workspace["memory:/artifacts/test-hexdigest-1.gz"] = "bar"

    accessor = datastores.Accessor(
        archive=datastores.Archive(
            artifacts=[
                datastores.Artifact(hexdigest="test-hexdigest-0"),
                datastores.Artifact(hexdigest="test-hexdigest-1"),
            ]
        ),
        layer=layer,
    )

    assert len(accessor) == 2
    assert [accessor[0], accessor[1]] == ["foo", "bar"]
    assert list(accessor) == ["foo", "bar"]
    assert accessor[:1] == ["foo"]
