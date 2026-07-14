PYTHON := $(shell command -v python3.13 2>/dev/null || command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null)
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help
.PHONY: help setup contract test lint fmt check clean

help:
	@echo "Network Anomaly Root-Cause Assistant"
	@echo ""
	@echo "  make setup      create .venv and install every dependency"
	@echo "  make contract   regenerate contracts/schemas.json from the models"
	@echo "  make test       validate the golden fixture and run the suite"
	@echo "  make lint       static analysis with ruff"
	@echo "  make fmt        format the codebase with ruff"
	@echo "  make check      lint followed by test"
	@echo "  make clean      remove the virtual environment and caches"

$(VENV):
	@test -n "$(PYTHON)" || { echo "Python 3.11 or newer is required. Install it with: brew install python@3.12"; exit 1; }
	@echo "creating virtual environment with $(PYTHON)"
	@$(PYTHON) -m venv $(VENV)
	@$(PIP) install --quiet --upgrade pip

setup: $(VENV)
	@$(PIP) install --quiet -r requirements.txt
	@echo "environment ready"
	@$(PY) --version

contract: setup
	@$(PY) contracts/schemas.py

test: setup
	@$(PY) -m pytest

lint: setup
	@$(PY) -m ruff check contracts src testbed eval tests

fmt: setup
	@$(PY) -m ruff format contracts src testbed eval tests

check: lint test

clean:
	@rm -rf $(VENV) .pytest_cache .ruff_cache
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "cleaned"
