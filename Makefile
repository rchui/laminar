include Make.rules

.PHONY: env
env:
	python -m virtualenv .venv --clear
	$(MAKE) upgrade

upgrade:
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade --requirement requirements.dev.txt

.PHONY: bash zsh
bash zsh:
	$(VENV) /bin/$@

.PHONY: format
format:
	black .
	isort .

.PHONY: lint
lint:
	black --check .
	flake8 laminar
	isort --check .
	mypy laminar
