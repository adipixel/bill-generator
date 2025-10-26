.PHONY: help install venv run act-build act-all

help:
	@echo "Makefile targets:"
	@echo "  install    - create .venv and install requirements"
	@echo "  run        - run the app using ./run.sh (requires .venv)"
	@echo "  act-build  - run the 'build' workflow job locally with act (linux)"
	@echo "  act-all    - run all build jobs locally with act"

install:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip && pip install -r requirements.txt

run:
	. .venv/bin/activate && ./run.sh

act-build:
	@if ! command -v act >/dev/null 2>&1; then echo "Please install 'act' (https://github.com/nektos/act) and Docker."; exit 1; fi
	act -j build-linux

act-all:
	@if ! command -v act >/dev/null 2>&1; then echo "Please install 'act' (https://github.com/nektos/act) and Docker."; exit 1; fi
	act -j build-linux -j build-windows -j build-macos
