VENV := . .venv/bin/activate &&
PYTHONPATH := ${PYTHONPATH}:${PWD}

export

DEFAULT: test

alembic:
	alembic upgrade head

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
	$(VENV) tox

shell:
	$(VENV) exec zsh

up:
	docker compose build
	docker compose up

.PHONY: \
	alembic \
	env \
	format \
	lock \
	test \
	shell \
	up
