import os
from typing import Optional

from pydantic import BaseModel


class Archive(BaseModel):
    length: Optional[int]
    hexdigest: str

    def uri(self, root: str) -> str:
        return os.path.join(root, "archive", f"{self.hexdigest}.gz")
