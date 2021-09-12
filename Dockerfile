# syntax = docker/dockerfile:latest
FROM python:3.9

WORKDIR /laminar

COPY requirements.txt ./
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    --mount=type=cache,target=/root/.cache/pip \
    apt-get update \
    && apt-get install -y --no-install-recommends \
    && pip install --upgrade pip \
    && pip install --requirement requirements.txt

COPY . ./
