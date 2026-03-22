# Quickstart

## 1) Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2) Add portfolio image

Put your screenshot at the project root as `portfolio.png`
or set `MARKET_REPORT_IMAGE_PATH` in `.env`.

## 3) Run pipeline

```bash
python -m bharat_market_pulse.report_pipeline
```

## 4) Run tests

```bash
PYTHONPATH=src pytest -q
```
