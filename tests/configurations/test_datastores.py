"""Tests for laminar.configurations.datastores"""

import io
import json
from pathlib import Path
from typing import Any, Dict, List, cast
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
        assert self.artifact.path(layer=layer) == f"{layer.flow.name}/artifacts/foo.gz"


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
            == f"{layer.flow.name}/archives/{layer.flow.execution}/{layer.name}/{layer.index}/test-archive.json"
        )
        assert (
            self.archive.path(layer=layer, index=0, name="test-archive", cache=True)
            == f"{layer.flow.name}/.cache/{layer.flow.execution}/{layer.name}/test-archive.json"
        )

    def test_parse(self) -> None:
        expected = {"artifacts": [{"dtype": "str", "hexdigest": "foo"}, {"dtype": "str", "hexdigest": "bar"}]}
        assert Archive.parse(expected).dict() == expected


class TestAccessor:
    @pytest.fixture(autouse=True)
    def _accessor(self, layer: Layer) -> None:
        workspace: Dict[str, Any] = layer.flow.configuration.datastore.cache
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
        items: List[str] = []
        for item in self.accessor:
            items.append(item)
        assert items == ["foo", "bar"]

    def test_slice(self) -> None:
        assert self.accessor[:1] == ["foo"]

    def test_index_out_of_bounds(self) -> None:
        with pytest.raises(IndexError):
            self.accessor[10]

    def test_index_other(self) -> None:
        with pytest.raises(TypeError):
            self.accessor[cast(int, "a")]


class TestDatastore:
    archive = Archive(artifacts=[Artifact(dtype="str", hexdigest="foo"), Artifact(dtype="str", hexdigest="bar")])
    datastore = DataStore(root="path/to/root/")
    record = Record(
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

    @patch("laminar.utils.fs.open")
    def test__read_archive(self, mock_open: Mock) -> None:
        mock_open.return_value = io.StringIO(json.dumps(self.archive.dict()))

        assert self.datastore._read_archive(path="path/to/archive") == self.archive

        mock_open.assert_called_once_with("path/to/root/path/to/archive", "r")

    @patch("laminar.utils.fs.open")
    def test_read_archive(self, mock_open: Mock, layer: Layer) -> None:
        mock_open.return_value = io.StringIO(json.dumps(self.archive.dict()))

        assert self.datastore.read_archive(layer=layer, index=0, name="test-archive") == self.archive

        mock_open.assert_called_once_with(
            "path/to/root/TestFlow/archives/test-execution/Layer/0/test-archive.json", "r"
        )

    @patch("laminar.utils.fs.open")
    def test__read_artifact(self, mock_open: Mock) -> None:
        mock_open.return_value = io.BytesIO(cloudpickle.dumps([True, False, None]))

        assert self.datastore._read_artifact(path="path/to/artifact", dtype="bool") == [True, False, None]

        mock_open.assert_called_once_with("path/to/root/path/to/artifact", "rb")

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

    @patch("laminar.configurations.datastores.DataStore.read_artifact")
    @patch("laminar.configurations.datastores.DataStore.read_archive")
    def test_read(self, mock_archive: Mock, mock_artifact: Mock, layer: Layer) -> None:
        self.datastore.read(layer=layer, index=0, name="test")

        mock_archive.assert_called_once_with(layer=layer, index=0, name="test")
        mock_artifact.assert_called_once_with(layer=layer, archive=mock_archive.return_value)

    @patch("laminar.utils.fs.open", new_callable=mock_open)
    def test__write_archive(self, mock_open: Mock) -> None:
        self.datastore._write_archive(path="path/to/archive", archive=self.archive)

        mock_open.assert_called_once_with("path/to/root/path/to/archive", "w")
        print(mock_open.return_value.write.call_args_list)
        assert mock_open.return_value.write.call_args_list == [
            call("{"),
            call('"artifacts"'),
            call(": "),
            call("["),
            call("{"),
            call('"dtype"'),
            call(": "),
            call('"str"'),
            call(", "),
            call('"hexdigest"'),
            call(": "),
            call('"foo"'),
            call("}"),
            call(", "),
            call("{"),
            call('"dtype"'),
            call(": "),
            call('"str"'),
            call(", "),
            call('"hexdigest"'),
            call(": "),
            call('"bar"'),
            call("}"),
            call("]"),
            call("}"),
        ]

    @patch("laminar.utils.fs.open", new_callable=mock_open)
    def test__write_artifact(self, mock_open: Mock) -> None:
        self.datastore._write_artifact(path="path/to/artifact", value="test-content")

        mock_open.assert_called_once_with("path/to/root/path/to/artifact", "wb")
        assert mock_open().write.call_args_list == [
            call(b"\x80\x05\x95\x10\x00\x00\x00\x00\x00\x00\x00\x8c\x0ctest-content\x94.")
        ]

    @patch("laminar.configurations.datastores.DataStore._write_artifact")
    @patch("laminar.configurations.datastores.DataStore._write_archive")
    def test_write(self, mock_write_archive: Mock, mock_write_artifact: Mock, layer: Layer) -> None:
        self.datastore.write(layer=layer, name="test-artifact", values=[True])

        mock_write_archive.assert_called_once_with(
            path="TestFlow/archives/test-execution/Layer/0/test-artifact.json",
            archive=Archive(
                artifacts=[
                    Artifact(dtype="bool", hexdigest="5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae")
                ]
            ),
        )
        mock_write_artifact.assert_called_once_with(
            path="TestFlow/artifacts/5280fce43ea9afbd61ec2c2a16c35118af29eafa08aa2f5f714e54dc9cceb5ae.gz",
            value=True,
        )

    @patch("laminar.utils.fs.open")
    def test__read_record(self, mock_open: Mock) -> None:
        mock_open.return_value = io.StringIO(json.dumps(self.record.dict()))

        assert self.datastore._read_record(path="path/to/record") == self.record

        mock_open.assert_called_once_with("path/to/root/path/to/record", "r")

    @patch("laminar.utils.fs.open")
    def test_read_record(self, mock_open: Mock, layer: Layer) -> None:
        mock_open.return_value = io.StringIO(json.dumps(self.record.dict()))

        assert self.datastore.read_record(layer=layer) == self.record

        mock_open.assert_called_once_with("path/to/root/TestFlow/.cache/test-execution/Layer/.record.json", "r")

    @patch("laminar.utils.fs.open", new_callable=mock_open)
    def test__write_record(self, mock_open: Mock) -> None:
        self.datastore._write_record(path="path/to/record", record=self.record)

        mock_open.assert_called_once_with("path/to/root/path/to/record", "w")
        assert mock_open.return_value.write.call_args_list == [
            call("{"),
            call('"flow"'),
            call(": "),
            call("{"),
            call('"name"'),
            call(": "),
            call('"test-flow"'),
            call("}"),
            call(", "),
            call('"layer"'),
            call(": "),
            call("{"),
            call('"name"'),
            call(": "),
            call('"test-layer"'),
            call("}"),
            call(", "),
            call('"execution"'),
            call(": "),
            call("{"),
            call('"splits"'),
            call(": "),
            call("2"),
            call("}"),
            call("}"),
        ]

    @patch("laminar.configurations.datastores.DataStore._write_record")
    def test_write_record(self, mock_open: Mock, layer: Layer) -> None:
        self.datastore.write_record(layer=layer, record=self.record)

        mock_open.assert_called_once_with(path="TestFlow/.cache/test-execution/Layer/.record.json", record=self.record)


class TestLocal:
    @pytest.fixture(autouse=True)
    def _datastore(self, tmp_path: Path) -> None:
        self.datastore = Local(root=str(tmp_path))

    def test_read_write(self, layer: Layer) -> None:
        self.datastore.write(layer=layer, name="test", values=[[True, False]])
        assert self.datastore.read(layer=layer, index=0, name="test") == [True, False]
