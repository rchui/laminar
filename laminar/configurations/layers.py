"""Configurations for laminar layers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Container:
    command: str = "python main.py"
    cpu: int = 1
    image: str = "python:3.9"
    memory: int = 1500
    workdir: str = "/laminar"
