"""Tests for laminar.configurations.datastores"""

import io
import json
from pathlib import Path
from typing import Any, Dict, cast
from unittest.mock import Mock, call, mock_open, patch

import cloudpickle
import pytest

from laminar import Layer
from laminar.configurations.datastores import Accessor, Archive, Artifact, DataStore, Local, Record


class TestArtifact:
    artifact = Artifact(dtype="str", hexdigest="foo")

    def test_dict(self) -> None:
        assert self.artifact.dict() == {"dtype": "str", "hexdigest": "foo"}

    def test_path(self, layer: Layer) -> None:
        assert self.artifact.path(layer=layer) == f"{layer.execution.flow.name}/artifacts/foo.gz"


class TestArchive:
    archive = Archive(artifacts=[Artifact(dtype="str", hexdigest="foo"), Artifact(dtype="str", hexdigest="bar")])

    def test_dict(self) -> None:
        assert self.archive.dict() == {
            "artifacts": [{"dtype": "str", "hexdigest": "foo"}, {"dtype": "str", "hexdigest": "bar"}]
        }

    def test_len(self) -> None:
        assert len(self.archive) == 2

    def test_path(self, layer: Layer) -> None:
        assert (
            self.archive.path(layer=layer, index=0, name="test-archive", cache=False)
            == f"{layer.execution.flow.name}/archives/{layer.execution.id}/{layer.name}/{layer.index}/test-archive.json"
        )
        assert (
            self.archive.path(layer=layer, index=0, name="test-archive", cache=True)
            == f"{layer.execution.flow.name}/.cache/{layer.execution.id}/{layer.name}/test-archive.json"
        )

    def test_parse(self) -> None:
        expected = {"artifacts": [{"dtype": "str", "hexdigest": "foo"}, {"dtype": "str", "hexdigest": "bar"}]}
        assert Archive.parse(expected).dict() == expected


class TestAccessor:
    @pytest.fixture(autouse=True)
    def _accessor(self, layer: Layer) -> None:
        workspace: Dict[str, Any] = layer.execution.flow.configuration.datastore.cache
        workspace["memory:///TestFlow/artifacts/test-hexdigest-0.gz"] = "foo"
        workspace["memory:///TestFlow/artifacts/test-hexdigest-1.gz"] = "bar"

        self.accessor = Accessor(
            archive=Archive(
                artifacts=[
                    Artifact(dtype="str", hexdigest="test-hexdigest-0"),
                    Artifact(dtype="str", hexdigest="test-hexdigest-1"),
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

    def test_for(self) -> None:
        assert [item for item in self.accessor] == ["foo", "bar"]

    def test_slice(self) -> None:
        assert self.accessor[:1] == ["foo"]

    def test_index_out_of_bounds(self) -> None:
        with pytest.raises(IndexError):
            self.accessor[10]

    def test_index_other(self) -> None:
        with pytest.raises(TypeError):
            self.accessor[cast(int, "a")]


class TestDatastore:
    @pytest.fixture(autouse=True)
    def _archive(self) -> None:
        self.archive = Archive(
            artifacts=[Artifact(dtype="str", hexdigest="foo"), Artifact(dtype="str", hexdigest="bar")]
        )

    @pytest.fixture(autouse=True)
    def _datastore(self) -> None:
        self.datastore = DataStore(root="path/to/root/")

    @pytest.fixture(autouse=True)
    def _record(self) -> None:
        self.record = Record(
            flow=Record.FlowRecord(name="test-flow"),
            layer=Record.LayerRecord(name="test-layer"),
            execution=Record.ExecutionRecord(splits=2),
        )

    def test_init(self) -> None:
        assert self.datastore.root == "path/to/root"

    def test_uri(self) -> None:
        assert self.datastore.uri(path="other/path") == "path/to/root/other/path"

    @patch("laminar.utils.fs.exists")
    def test_exists(self, mock_exists: Mock) -> None:
        self.datastore.exists(path="path/to/file")

        mock_exists.assert_called_once_with(uri="path/to/root/path/to/file")

    def test_protocol(self) -> None:
        mock_protocol = Mock()
        self.datastore.protocol(str)(mock_protocol)
        assert self.datastore.protocols["builtins.str"] == mock_protocol.return_value

    @patch("laminar.utils.fs.open")
    def test_read_archive(self, mock_open: Mock, layer: Layer) -> None:
        mock_open.return_value = io.StringIO(json.dumps(self.archive.dict()))

        assert self.datastore.read_archive(layer=layer, index=0, name="test-archive") == self.archive

        mock_open.assert_called_once_with(
            "path/to/root/TestFlow/archives/test-execution/Layer/0/test-archive.json", "rb"
        )

    @patch("laminar.utils.fs.open")
    def test_read_artifact(self, mock_open: Mock, layer: Layer) -> None:
        mock_open.return_value = io.BytesIO(cloudpickle.dumps("test-value"))

        assert (
            self.datastore.read_artifact(
                layer=layer, archive=Archive(artifacts=[Artifact(dtype="str", hexdigest="foo")])
            )
            == "test-value"
        )

        mock_open.assert_called_once_with("path/to/root/TestFlow/artifacts/foo.gz", "rb")

    def test_read_artifact_accessor(self, layer: Layer) -> None:
        assert self.datastore.read_artifact(layer=layer, archive=self.archive) == Accessor(
            archive=self.archive, layer=layer
        )

    @patch("laminar.configurations.datastores.DataStore._read")
    def test_read(self, mock_read: Mock, layer: Layer) -> None:
        mock_read.return_value.__len__.return_value = 1

        self.datastore.read(layer=layer, index=0, name="test")

        assert mock_read.call_args_list == [
            call(
                uri="path/to/root/TestFlow/archives/test-execution/Layer/0/test.json",
                dtype="laminar.configurations.datastores.ArchiveProtocol",
            ),
            call(
                uri=self.datastore.uri(path=mock_read.return_value.artifacts[0].path.return_value),
                dtype=mock_read.return_value.artifacts[0].dtype,
            ),
        ]

    @patch("laminar.utils.fs.open", new_callable=mock_open)
    def test_write_archive(self, mock_open: Mock, layer: Layer) -> None:
        assert (
            self.datastore.write_archive(layer=layer, name="test-archive", artifacts=self.archive.artifacts)
            == self.archive
        )

        mock_open.assert_called_once_with(
            "path/to/root/TestFlow/archives/test-execution/Layer/0/test-archive.json", "wb"
        )
        mock_open.return_value.write.assert_called_once_with(
            b'{"artifacts": [{"dtype": "str", "hexdigest": "foo"}, {"dtype": "str", "hexdigest": "bar"}]}'
        )

    @patch("laminar.utils.fs.open", new_callable=mock_open)
    def test_write_artifact(self, mock_open: Mock, layer: Layer) -> None:
        assert self.datastore.write_artifact(layer=layer, value="test-value") == Artifact(
            dtype="builtins.str", hexdigest="7d3d5dd741934c11ce55c08d83052780db2f29438238f602afbd51b177a98b7f"
        )

        mock_open.assert_called_once_with(
            "path/to/root/TestFlow/artifacts/7d3d5dd741934c11ce55c08d83052780db2f29438238f602afbd51b177a98b7f.gz", "wb"
        )
        mock_open.return_value.write.assert_called_once_with(
            b"\x80\x05\x95\x0e\x00\x00\x00\x00\x00\x00\x00\x8c\ntest-value\x94."
        )

    @patch("laminar.configurations.datastores.DataStore._write")
    def test_write(self, mock_write: Mock, layer: Layer) -> None:
        self.datastore.write(layer=layer, name="test-artifact", values=[True])

        assert mock_write.call_args_list == [
            call(
                value=True,
                uri=(
                    "path/to/root/TestFlow/artifacts/"
                    "5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae.gz"
                ),
                dtype="builtins.bool",
            ),
            call(
                value=Archive(
                    artifacts=[
                        Artifact(
                            dtype="builtins.bool",
                            hexdigest="5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae",
                        )
                    ]
                ),
                uri="path/to/root/TestFlow/archives/test-execution/Layer/0/test-artifact.json",
                dtype="laminar.configurations.datastores.ArchiveProtocol",
            ),
        ]

    @patch("laminar.utils.fs.open")
    def test_read_record(self, mock_open: Mock, layer: Layer) -> None:
        mock_open.return_value = io.StringIO(json.dumps(self.record.dict()))

        assert self.datastore.read_record(layer=layer) == self.record

        mock_open.assert_called_once_with("path/to/root/TestFlow/.cache/test-execution/Layer/.record.json", "rb")

    @patch("laminar.utils.fs.open", new_callable=mock_open)
    def test_write_record(self, mock_write: Mock, layer: Layer) -> None:
        self.datastore.write_record(layer=layer, record=self.record)

        mock_write.assert_called_once_with("path/to/root/TestFlow/.cache/test-execution/Layer/.record.json", "wb")
        mock_write.return_value.write.assert_called_once_with(
            b'{"flow": {"name": "test-flow"}, "layer": {"name": "test-layer"}, "execution": {"splits": 2}}'
        )


class TestLocal:
    @pytest.fixture(autouse=True)
    def _datastore(self, tmp_path: Path) -> None:
        self.datastore = Local(root=str(tmp_path))

    def test_read_write(self, layer: Layer) -> None:
        self.datastore.write(layer=layer, name="test", values=[[True, False]])
        assert self.datastore.read(layer=layer, index=0, name="test") == [True, False]
