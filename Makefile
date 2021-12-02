include Make.rules

.PHONY: clear
clear:
	rm -rf .laminar

.PHONY: docs
docs:
	sphinx-build -a docs/source docs/

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

.PHONY: open
open: docs
	open docs/index.html

.PHONY: run
run: test
	docker build -t test .
	docker system prune --force
	python main.py

.PHONY: test
test:
	black --check .
	pytest --cov laminar --cov-report term-missing --flake8 --mypy --isort
