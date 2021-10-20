import os
from typing import Optional

from pydantic import BaseModel


class Artifact(BaseModel):
    archive: "Archive"

    @staticmethod
    def root(root: str) -> str:
        return os.path.join(root, "artifacts")

    def uri(self, root: str) -> str:
        return os.path.join(self.root(root), f"{self.archive.hexdigest}.gz")


class Archive(BaseModel):
    length: Optional[int]
    hexdigest: str

    @staticmethod
    def uri(*, root: str, flow: str, execution: str, layer: str, artifact: str) -> str:
        return os.path.join(root, flow, execution, layer, f"{artifact}.json")

    @property
    def artifact(self) -> Artifact:
        return Artifact(archive=self)


Artifact.update_forward_refs()
