"""Tests for laminar.configurations.datastores"""

import dataclasses
from unittest.mock import Mock

from laminar.configurations import datastores


def test_artifact() -> None:
    artifact = datastores.Artifact(hexdigest="foo")

    assert dataclasses.asdict(artifact) == {"hexdigest": "foo"}
    assert artifact.path() == "artifacts/foo.gz"


def test_archive() -> None:
    archive = datastores.Archive(artifacts=[datastores.Artifact(hexdigest="foo"), datastores.Artifact(hexdigest="bar")])
    layer = Mock()

    assert dataclasses.asdict(archive) == {"artifacts": [{"hexdigest": "foo"}, {"hexdigest": "bar"}]}
    assert len(archive) == 2
    assert (
        datastores.Archive(artifacts=[datastores.Artifact(hexdigest="foo")]).path(
            layer=layer, index=0, name="test-archive"
        )
        == f"{layer.flow.name}/{layer.flow.execution}/{layer.name}/{layer.index}/test-archive.json"
    )
