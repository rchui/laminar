# syntax = docker/dockerfile:latest
FROM python:3.8-slim

WORKDIR /laminar

COPY requirements.txt ./
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    --mount=type=cache,target=/root/.cache/pip \
    apt-get update \
    && apt-get install -y --no-install-recommends \
    && python -m pip install --upgrade pip \
    && python -m pip install --requirement requirements.txt \
    && rm requirements.txt
