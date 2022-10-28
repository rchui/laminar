# syntax = docker/dockerfile:latest

ARG PYTHON_VERSION=3.8
ARG WHEELDIR=/opt/python${PYTHON_VERSION}/wheels/

# --- Setup build environment

FROM python:${PYTHON_VERSION}-slim as base

ARG WHEELDIR

WORKDIR /laminar

RUN --mount=type=cache,mode=0755,target=/var/cache/apt \
    --mount=type=cache,mode=0755,target=/var/lib/apt \
    --mount=type=cache,mode=0755,target=/root/.cache/pip \
        apt-get update \
            && apt-get upgrade -y \
            && apt-get clean \
            && python -m pip install --upgrade pip wheel

# --- Build laminar package wheels

FROM base as builder

COPY . ./

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
        python -m pip wheel --wheel-dir ${WHEELDIR} .

# --- Install laminar packages from wheels

FROM python:3.8-slim as test

ARG WHEELDIR

WORKDIR /laminar

COPY --from=builder ${WHEELDIR} ${WHEELDIR}

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
        python -m pip install --no-index --find-links=${WHEELDIR} laminar \
            && rm -rf ${WHEELDIR}

COPY main.py ./

# --- Create laminar release image

FROM base as release

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
        python -m pip install laminar
