VENV := . .venv/bin/activate &&
PYTHONPATH := ${PYTHONPATH}:${PWD}

export

DEFAULT: test

alembic-upgrade:
	alembic upgrade head

alembic-revision:
	docker run \
		--name postgres \
		--detach \
		--interactive \
		--tty \
		--rm \
		--env POSTGRES_DB=laminar \
		--env POSTGRES_USER=laminar \
		--env POSTGRES_PASSWORD=laminar \
		-p 5432:5432 \
		postgres
	until pg_isready -U laminar -h localhost; do echo 'Waiting for postgres...'; sleep 2; done
	$(MAKE) alembic-upgrade
	alembic revision --autogenerate
	docker stop postgres

env:
	virtualenv .venv --clear
	$(VENV) pip install --upgrade pip
	$(VENV) pip install --requirement requirements.txt.lock
	$(VENV) pip install --editable .

format:
	$(VENV) black .
	$(VENV) isort .

lock:
	docker run \
		--interactive \
		--tty \
		--rm \
		--workdir /src \
		--volume $(PWD):/src \
		--volume $(shell pip cache dir):/root/.cache/pip \
		python:3.6 \
		/bin/bash -c " \
			set -exo pipefail; \
			python -m pip install --upgrade pip pip-tools; \
			pip-compile requirements.txt.dev --output-file requirements.txt.lock --no-header --verbose; \
		"
	$(MAKE) env

test:
	$(VENV) nox --list
	$(VENV) nox

shell:
	$(VENV) exec zsh

up:
	docker compose build
	docker compose up

.PHONY: \
	alembic-upgrade \
	alembic-revision \
	env \
	format \
	lock \
	test \
	shell \
	up
