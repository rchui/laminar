# syntax = docker/dockerfile:latest
FROM python:3.8-slim as requirements

WORKDIR /laminar

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    --mount=type=cache,target=/root/.cache/pip \
    apt-get update \
    && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && python -m pip install --upgrade pip wheel

FROM requirements as release

COPY . ./

RUN python -m pip install . \
    && rm -rf ./*

FROM release as test

COPY main.py ./
