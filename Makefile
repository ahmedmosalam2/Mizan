# ============================================================
# Mizan Benchmark — Makefile
# ============================================================
#
# Usage:
#   make env              Install core + dev dependencies
#   make env FW=crewai    Install + crewai extra
#   make run              Run single scenario (FW + SC required)
#   make matrix           Run full benchmark matrix
#   make lint             Ruff + mypy
#   make test             pytest
#   make clean            Remove build artifacts
#
# Examples:
#   make run FW=crewai SC=s01_task_decomposition
#   make run FW=crewai SC=s07_pii_redaction_ar VERBOSE=--verbose
#   make matrix FW=crewai CATEGORY=safety
# ============================================================

FW       ?= crewai
SC       ?= s01_task_decomposition
VERBOSE  ?=
REPEAT   ?= 1
CATEGORY ?=

PYTHON   := python
PIP      := pip
UVICORN  := uvicorn

.PHONY: env run matrix lint test clean help

## ── Setup ─────────────────────────────────────────────────────

env:
	$(PIP) install -e ".[dev]"
ifdef FW
	$(PIP) install -e ".[$(FW)]"
endif
	@echo "✅ Environment ready"

## ── Run Scenarios ─────────────────────────────────────────────

run:
	$(PYTHON) runner/run_scenario.py --framework $(FW) --scenario $(SC) $(VERBOSE)

matrix:
	$(PYTHON) runner/run_matrix.py \
		$(if $(FW),--framework $(FW),) \
		$(if $(CATEGORY),--category $(CATEGORY),) \
		--repeat $(REPEAT)

## ── Quality ───────────────────────────────────────────────────

lint:
	ruff check shared/ scenarios/ frameworks/ runner/
	mypy shared/ --ignore-missing-imports

format:
	ruff format shared/ scenarios/ frameworks/ runner/

test:
	pytest shared/ -v --tb=short

## ── Cleanup ───────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean"

help:
	@echo ""
	@echo "  Mizan Benchmark — Available Commands"
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  make env              Install dependencies"
	@echo "  make env FW=crewai    Install + CrewAI"
	@echo "  make run FW=crewai SC=s01_task_decomposition"
	@echo "  make matrix FW=crewai"
	@echo "  make lint             Ruff + mypy"
	@echo "  make test             pytest"
	@echo "  make clean            Remove build artifacts"
	@echo ""
