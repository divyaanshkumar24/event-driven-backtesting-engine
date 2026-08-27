PYTHON := python3.11
VENV := .venv
VENV_BIN := $(VENV)/bin

.PHONY: venv test lint format clean

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -e ".[dev]"

test:
	$(VENV_BIN)/pytest

lint:
	$(VENV_BIN)/ruff check .

format:
	$(VENV_BIN)/ruff format .

clean:
	rm -rf $(VENV) .pytest_cache **/__pycache__
