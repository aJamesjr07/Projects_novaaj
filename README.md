# Bharat Market Pulse

Bharat Market Pulse is a portfolio intelligence pipeline for Indian markets.

It extracts portfolio holdings from screenshots or structured data,
collects signals from trusted financial sources,
analyzes sentiment and triggers,
and produces structured investment intelligence reports.

## Project structure

- `src/` — Python application
- `docs/` — Quarto documentation site
- `tests/` — unit tests

## Quickstart

1. create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

2. install dependencies

```bash
pip install -e .[dev]
```

3. configure environment

```bash
cp .env.example .env
```

4. run pipeline

```bash
python -m bharat_market_pulse.report_pipeline
```

## Developer commands

```bash
make setup   # create venv + install editable package + dev tools
make lint    # ruff lint
make format  # ruff formatter
make test    # pytest
make check   # lint + format-check + tests
make run     # run pipeline
```

## Disclaimer

This project is a research-assist and portfolio-monitoring tool. It is not financial advice.
Output quality depends on source quality and extraction quality.
