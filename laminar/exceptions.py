"""Shared laminar exceptions."""


class ExecutionError(Exception):
    """An error occured during execution."""


class FlowError(Exception):
    """An error occured in a Flow."""


class LayerError(Exception):
    """An error occured in a Layer."""
