VENV := . .venv/bin/activate &&

DEFAULT: test

env:
	virtualenv .venv --clear
	$(VENV) pip install --upgrade pip
	$(VENV) pip install --requirement requirements.dev.txt

test:
	$(VENV) tox

shell:
	$(VENV) /bin/zsh

.PHONY: \
	env \
	test \
	shell
