"""Configuraitons for laminar data sources."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cloudpickle
from smart_open import open


@dataclass(frozen=True)
class DataSource:
    root: str

    def _read(self, uri: str) -> Any:
        with open(uri, "rb") as file:
            return cloudpickle.load(file)

    def read(self, uri: str) -> Any:
        """Read an artifact from the laminar archive.

        Args:
            uri (str): URI of the artifact to read.

        Returns:
            Any: Value of the artifact.
        """

        return self._read(uri)

    def _write(self, uri: str, artifact: Any) -> None:
        with open(uri, "wb") as file:
            cloudpickle.dump(artifact, file)

    def write(self, uri: str, artifact: Any) -> None:
        """Write an artifact to the laminar archive.

        Args:
            uri (str): URI of the artifact to write.
            artifact (Any): Value of the artifact.
        """

        self._write(uri, artifact)


@dataclass(frozen=True)
class Local(DataSource):
    root: str = str(Path.cwd() / ".laminar")

    def write(self, uri: str, artifact: Any) -> None:
        Path(uri).parent.mkdir(parents=True, exist_ok=True)
        self._write(uri, artifact)


@dataclass(frozen=True)
class S3(DataSource):
    bucket: str
    prefix: str

    @property
    def root(self) -> str:
        return f"s3://{self.bucket}/{self.prefix.strip('/')}"
