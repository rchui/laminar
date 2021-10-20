"""Configuraitons for laminar data sources."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cloudpickle
from smart_open import open

from laminar import models


@dataclass(frozen=True)
class DataSource:
    root: str

    def _read(self, uri: str) -> Any:
        # Read the archive
        with open(uri, "r") as file:
            archive = models.Archive.parse_raw(file.read())

        # Read the artifact value
        with open(archive.uri(self.root), "rb") as file:
            return cloudpickle.load(file)

    def read(self, *, flow: str, execution: str, layer: str, artifact: str) -> Any:
        """Read an artifact from the laminar archive.

        Args:
            uri (str): URI of the artifact to read.

        Returns:
            Any: Value of the artifact.
        """

        return self._read(os.path.join(self.root, flow, execution, layer, artifact))

    def _write(self, uri: str, artifact: Any) -> None:
        contents = cloudpickle.dumps(artifact)
        archive = models.Archive(
            length=len(artifact) if hasattr(artifact, "__len__") else None,
            hexdigest=hashlib.sha256(contents).hexdigest(),
        )

        # Write the archive
        with open(uri, "w") as file:
            file.write(archive.json())

        # Write the artifact value
        with open(archive.uri(self.root)) as file:
            file.write(contents)

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, value: Any) -> None:
        """Write an artifact to the laminar archive.

        Args:
            uri (str): URI of the artifact to write.
            artifact (Any): Value of the artifact.
        """

        self._write(os.path.join(self.root, flow, execution, layer, artifact), value)


@dataclass(frozen=True)
class Local(DataSource):
    root: str = str(Path.cwd() / ".laminar")

    def write(self, *, flow: str, execution: str, layer: str, artifact: str, value: Any) -> None:
        uri = os.path.join(self.root, flow, execution, layer, artifact)
        Path(uri).parent.mkdir(parents=True, exist_ok=True)
        (Path(self.root) / "archive").mkdir(parents=True, exist_ok=True)

        self._write(uri, value)


@dataclass(frozen=True)
class S3(DataSource):
    bucket: str
    prefix: str

    @property
    def root(self) -> str:
        return f"s3://{self.bucket}/{self.prefix.strip('/')}"
