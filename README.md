# Bharat Market Pulse

Bharat Market Pulse is a Python + Quarto project that converts portfolio screenshots into a concise India-focused market intelligence report with actionable `Buy/Hold/Sell` outputs, confidence scoring, and citations.

## Repository description

India-focused portfolio intelligence pipeline with OCR/LLM extraction, source-weighted analysis, Quarto docs, tests, and GitHub Actions CI.

## Project structure

- `src/bharat_market_pulse/` — core Python package
- `tests/` — unit tests (analyzer/config/report logic)
- `docs/` — project docs and learnings
- `.github/workflows/` — Quarto render + Python CI
- `index.qmd` / `_quarto.yml` — Quarto website

## Quickstart

See [`docs/quickstart.md`](docs/quickstart.md).

## Run

```bash
python -m bharat_market_pulse.report_pipeline
```

## Test

```bash
PYTHONPATH=src pytest -q
```
