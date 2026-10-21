PYTHON ?= python3
BIN := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/; fi)

.PHONY: check
check:
	$(BIN)ruff check .
	$(BIN)mypy crc
	$(BIN)lint-imports
	$(BIN)pytest -q
