include Make.rules
include Make.tf

.PHONY: clean
clean: clear
	rm -rf __pycache__ .mypy_cache .pytest_cache .venv .coverage

.PHONY: clear
clear:
	rm -rf .laminar
	rm -rf docs/source/api docs/html

.PHONY: docs
docs:
	sphinx-build -a docs/source docs/html

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
	black -C .
	isort .

.PHONY: open
open: docs
	open docs/html/index.html

.PHONY: run
run:
	docker build -t rchui/laminar:3.8 .
	docker build -t rchui/laminar:test-local -f Dockerfile.test .
	docker system prune --force
	python main.py

.PHONY: test
test:
	black .
	pytest -m "not flow" --cov laminar --cov-report term-missing --flake8 --mypy --isort
	pytest -m "flow"
