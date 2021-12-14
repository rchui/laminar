"""Shared laminar exceptions."""


class ExecutionError(Exception):
    """An error that occured during execution."""


class FlowError(Exception):
    """An error that occured during Flow definition."""


class LayerError(Exception):
    """An error that occured during Layer definition."""


class SchedulerError(Exception):
    """An error that occured during Flow scheduling."""
