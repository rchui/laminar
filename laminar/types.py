from typing import Callable

from pydantic import BaseModel

Step = Callable[..., BaseModel]
