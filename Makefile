.PHONY:
all: test smoke

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
		docs/source/api \
		laminar.egg-info

.PHONY: docs
docs:
	$(VENV) sphinx-build -a docs/source docs/html

.PHONY: env
env: venv upgrade

.PHONY: format
format:
	$(VENV) black -C .
	$(VENV) isort .
	$(VENV) ruff --fix --show-fixes --show-source .

.PHONY: lint
lint:
	$(VENV) black --version && black --check .
	$(VENV) isort --version && isort --check-only .
	$(VENV) ruff --version && ruff --diff .
	$(VENV) mypy --version && mypy .

.PHONY: open
open: docs
	open docs/html/index.html

.PHONY: release
release:
	docker build --build-arg BUILDKIT_INLINE_CACHE=1 --tag rchui/laminar:3.8 --target release .
	docker system prune --force

.PHONY: smoke
smoke:
	docker build --build-arg BUILDKIT_INLINE_CACHE=1 --tag rchui/laminar:3.8 --target test .
	docker system prune --force
	$(VENV) python main.py

.PHONY: tag
tag:
	python tests/tag.py

.PHONY: test
test: lint
	$(VENV) pytest -m "not flow" --cov laminar --cov-report term-missing
	$(VENV) pytest -m "flow"

.PHONY: upgrade
upgrade:
	$(VENV) $(INSTALL) --upgrade pip wheel
	$(VENV) $(INSTALL) --constraint constraints.txt --upgrade --editable .[dev]

.PHONY: venv
venv:
	python -m venv .venv --clear
