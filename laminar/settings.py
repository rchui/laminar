"""Access for execution specific environment variables."""

from typing import Optional

from pydantic import BaseSettings


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

    class Execution(BaseSettings):
        class Config:
            env_prefix = "LAMINAR_EXECUTION_"

        #: ID of the current execution
        id: Optional[str] = None
        #: True if execution is being retried, else False
        retry: bool = False

    class Flow(BaseSettings):
        class Config:
            env_prefix = "LAMINAR_FLOW_"

        #: Name of the currently running flow
        name: Optional[str] = None

    class Layer(BaseSettings):
        class Config:
            env_prefix = "LAMINAR_LAYER_"

        #: Current layer attempt
        attempt: Optional[int] = None
        #: Index of the layer the layer splits
        index: Optional[int] = None
        #: Name of the currently running layer
        name: Optional[str] = None
        #: Number of splits in the layer
        splits: Optional[int] = None

    @property
    def execution(self) -> Execution:
        """Get information about the current flow execution."""
        return self.Execution()

    @property
    def flow(self) -> Flow:
        """Get information about the current flow."""
        return self.Flow()

    @property
    def layer(self) -> Layer:
        """Get information about the current layer execution."""
        return self.Layer()


current = Current()
