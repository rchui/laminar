VENV := . .venv/bin/activate &&
PYTHONPATH := ${PYTHONPATH}:${PWD}

export

DEFAULT: test

env:
	virtualenv .venv --clear
	$(VENV) pip install --upgrade pip
	$(VENV) pip install --requirement requirements.dev.txt
	$(VENV) pip install --editable .

format:
	$(VENV) black .
	$(VENV) isort .

test:
	$(VENV) tox

shell:
	$(VENV) /bin/zsh

.PHONY: \
	env \
	test \
	shell
