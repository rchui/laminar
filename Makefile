include Make.rules

.PHONY: clear
clear:
	rm -rf .laminar

.PHONY: env
env:
	python -m virtualenv .venv --clear
	$(MAKE) upgrade

.PHONY: upgrade
upgrade:
	$(PIP) --upgrade pip
	$(PIP) --upgrade --requirement requirements.dev.txt

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
	mypy laminar tests

.PHONY: run
run: lint
	docker build -t test .
	docker system prune --force
	python main.py

.PHONY: test
test: lint
	pytest -vv -r Efs --cov laminar --cov-report term-missing --durations 10 --failed-first --strict-markers tests
