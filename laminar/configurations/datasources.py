"""Configuraitons for laminar data sources."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cloudpickle
from smart_open import open


@dataclass(frozen=True)
class DataSource:
    def read(self, uri: str) -> Any:
        with open(uri, "rb") as file:
            return cloudpickle.load(file)

    def write(self, uri: str, artifact: Any) -> None:
        with open(uri, "wb") as file:
            cloudpickle.dump(artifact, file)


@dataclass(frozen=True)
class Local(DataSource):
    root: str = str(Path.cwd() / ".laminar")


@dataclass(frozen=True)
class S3(DataSource):
    bucket: str
    prefix: str

    @property
    def root(self) -> str:
        return f"s3://{self.bucket}/{self.prefix.strip('/')}"
