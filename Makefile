.PHONY: setup test lint format check run

setup:
	python -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip && pip install -e .[dev]

test:
	. .venv/bin/activate && PYTHONPATH=src pytest

lint:
	. .venv/bin/activate && ruff check .

format:
	. .venv/bin/activate && ruff format .

check:
	. .venv/bin/activate && ruff check . && ruff format --check . && PYTHONPATH=src pytest

run:
	. .venv/bin/activate && python -m bharat_market_pulse.report_pipeline
