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
	$(VENV) black -C .
	$(VENV) isort .

.PHONY: lint
lint:
	$(VENV) black --version && black --check .
	$(VENV) isort --version && isort --check-only .
	$(VENV) flake8 --version && flake8 .
	$(VENV) mypy --version && mypy .

.PHONY: open
open: docs
	open docs/html/index.html

.PHONY: run
run:
	docker build --build-arg BUILDKIT_INLINE_CACHE=1 --tag rchui/laminar:3.8 .
	docker build --build-arg BUILDKIT_INLINE_CACHE=1 --tag rchui/laminar:test-local -f Dockerfile.test .
	docker system prune --force
	python main.py

.PHONY: tag
tag:
	python tests/tag.py

.PHONY: test
test: lint
	$(VENV) pytest -m "not flow" --cov laminar --cov-report term-missing
	$(VENV) pytest -m "flow"

.PHONY: upgrade
upgrade:
	$(VENV) $(INSTALL) pip wheel
	$(VENV) $(INSTALL) --requirement requirements.txt
	$(VENV) $(INSTALL) --requirement requirements.dev.txt

.PHONY: venv
venv:
	python -m venv .venv --clear
