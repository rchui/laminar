include Make.build
include Make.rules
include Make.tf

.PHONY: bash zsh
bash zsh:
	$(VENV) /bin/$@

.PHONY: clean
clean: clear
	rm -rf \
		__pycache__ \
		.coverage \
		.mypy_cache \
		.pytest_cache \
		.venv

.PHONY: clear
clear:
	rm -rf \
		.laminar \
		build \
		dist \
		docs/html \
		docs/source/api

.PHONY: docs
docs:
	sphinx-build -a docs/source docs/html

.PHONY: env
env: venv upgrade

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

.PHONY: tag
tag:
	python tests/tag.py

.PHONY: test
test:
	$(VENV) black .
	$(VENV) pytest -m "not flow" --cov laminar --cov-report term-missing --flake8 --mypy --isort
	$(VENV) pytest -m "flow"

.PHONY: upgrade
upgrade:
	$(VENV) $(INSTALL) pip
	$(VENV) $(INSTALL) --requirement requirements.txt
	$(VENV) $(INSTALL) --requirement requirements.dev.txt

.PHONY: venv
venv:
	python -m venv .venv --clear
