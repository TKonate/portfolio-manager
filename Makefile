# Portfolio Manager — development shortcuts.
#
#   make install     create .venv and install the package with dev tools
#   make test        run the test suite
#   make lint        ruff
#   make typecheck   mypy
#   make coverage    tests with a coverage report
#   make check       lint + typecheck + tests (what CI runs)
#   make demo        rebuild the demo portfolio
#   make serve       serve the demo portfolio in the browser
#   make clean       remove caches and build artefacts

PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: install test lint typecheck coverage check demo serve clean

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

test:
	$(BIN)/python -m pytest -q

lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

typecheck:
	$(BIN)/mypy

coverage:
	$(BIN)/python -m pytest -q --cov=pfm --cov-report=term-missing

check: lint typecheck test

demo:
	$(BIN)/python examples/build_demo.py
	$(BIN)/python -m pfm -c examples/portfolio/config.json check
	$(BIN)/python -m pfm -c examples/portfolio/config.json stats --write
	$(BIN)/python -m pfm -c examples/portfolio/config.json index

serve:
	$(BIN)/python -m pfm -c examples/portfolio/config.json serve --open --verbose

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
