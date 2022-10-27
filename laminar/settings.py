"""Access for execution specific environment variables."""

import os
from typing import Optional


def get(prefix: str, attr: str) -> Optional[str]:
    """Get environment variable."""
    return os.environ.get(f"{prefix}{attr.upper()}")


def coerce_bool(prefix: str, attr: str) -> bool:
    """Coerce environment variable to a boolean."""
    return (get(prefix, attr) or "False") == "True"


def coerce_optional_str(prefix: str, attr: str) -> Optional[str]:
    """Coerce environment variable to an optional string."""
    return get(prefix, attr)


def coerce_optional_int(prefix: str, attr: str) -> Optional[int]:
    """Coerce environment variable to an optional integer."""
    value = get(prefix, attr)
    return None if value is None else int(value)


class Current:
    """Get information about the current execution environment.

    Usage::

        from laminar.settings import current

        current.execution.id
        current.flow.name
        current.layer.attempt
        current.layer.index
        current.layer.name
        currnet.layer.splits
    """

    class Execution:
        class Env:
            prefix = "LAMINAR_EXECUTION_"

        @property
        def id(self) -> Optional[str]:
            """ID of the current execution"""
            return coerce_optional_str(self.Env.prefix, "id")

        @property
        def retry(self) -> bool:
            """True if execution is being retried, else False"""
            return coerce_bool(self.Env.prefix, "retry")

    class Flow:
        class Env:
            prefix = "LAMINAR_FLOW_"

        @property
        def name(self) -> Optional[str]:
            """Name of the currently running flow"""
            return coerce_optional_str(self.Env.prefix, "name")

    class Layer:
        class Env:
            prefix = "LAMINAR_LAYER_"

        @property
        def attempt(self) -> Optional[int]:
            """Current layer attempt"""
            return coerce_optional_int(self.Env.prefix, "attempt")

        @property
        def index(self) -> Optional[int]:
            """Index of the layer the layer splits"""
            return coerce_optional_int(self.Env.prefix, "index")

        @property
        def name(self) -> Optional[str]:
            """Name of the currently running layer"""
            return coerce_optional_str(self.Env.prefix, "name")

        @property
        def splits(self) -> Optional[int]:
            """Number of splits in the layer"""
            return coerce_optional_int(self.Env.prefix, "splits")

    execution = Execution()
    flow = Flow()
    layer = Layer()


current = Current()
