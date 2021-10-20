"""Configuraitons for laminar data sources."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cloudpickle
from smart_open import open

from laminar.models import Archive, Artifact


@dataclass(frozen=True)
class DataSource:
    root: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.rstrip("/"))

    def _read(self, uri: str) -> Any:
        # Read the archive
        with open(uri, "r") as file:
            archive = Archive.parse_raw(file.read())

        # Read the artifact value
        with open(archive.artifact.uri(self.root), "rb") as file:
            return cloudpickle.load(file)

    def read(self, *, flow: str, execution: str, layer: str, artifact: str) -> Any:
        """Read an artifact from the laminar datasource.

        Args:
            uri (str): URI of the artifact to read.

        Returns:
            Any: Value of the artifact.
        """

        return self._read(Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact))

    def _write(self, uri: str, value: Any) -> None:
        contents = cloudpickle.dumps(value)
        archive = Archive(
            length=len(value) if hasattr(value, "__len__") else None,
            hexdigest=hashlib.sha256(contents).hexdigest(),
        )

        # Write the archive
        with open(uri, "w") as file:
            file.write(archive.json())

        # Write the artifact value
        with open(archive.artifact.uri(self.root), "wb") as file:
            file.write(contents)

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, value: Any) -> None:
        """Write an artifact to the laminar datasource.

        Args:
            uri (str): URI of the artifact to write.
            artifact (Any): Value of the artifact.
        """

        self._write(Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact), value)


@dataclass(frozen=True)
class Local(DataSource):
    root: str = str(Path.cwd() / ".laminar")

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, value: Any) -> None:
        uri = Archive.uri(root=self.root, flow=flow, execution=execution, layer=layer, artifact=artifact)

        Path(uri).parent.mkdir(parents=True, exist_ok=True)
        Path(Artifact.root(self.root)).mkdir(parents=True, exist_ok=True)

        self._write(uri, value)


@dataclass(frozen=True)
class S3(DataSource):
    ...
