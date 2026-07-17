.PHONY:
all: test smoke

include Make.build
include Make.rules
include Make.tf

.PHONY: bash zsh
bash zsh:
	$(RUN) /bin/$@

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
	$(RUN) sphinx-build -a docs/source docs/html

.PHONY: env
env:
	uv sync --group dev

.PHONY: format
format:
	$(RUN) ruff check --fix --show-fixes .
	$(RUN) ruff format .

.PHONY: lint
lint:
	$(RUN) ruff --version && $(RUN) ruff check .
	$(RUN) ruff format --diff .
	$(RUN) mypy --version && $(RUN) mypy .

.PHONY: open
open: docs
	open docs/html/index.html

.PHONY: release
release:
	docker build --build-arg BUILDKIT_INLINE_CACHE=1 --tag rchui/laminar:3.10 --target release .
	docker system prune --force

.PHONY: smoke
smoke:
	docker build --build-arg BUILDKIT_INLINE_CACHE=1 --tag rchui/laminar:3.10 --target test .
	docker system prune --force
	$(RUN) python main.py

.PHONY: tag
tag:
	$(RUN) python tests/tag.py

.PHONY: test
test: lint
	$(RUN) pytest -m "not flow" --cov laminar --cov-report term-missing
	$(RUN) pytest -m "flow"

.PHONY: upgrade
upgrade:
	uv lock --upgrade
	uv sync --group dev
