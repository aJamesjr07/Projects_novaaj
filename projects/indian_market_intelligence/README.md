# Indian Market Intelligence Report Pipeline

A self-documenting Python pipeline to convert a portfolio screenshot into a daily **Indian Market Intelligence Report**.

## Phases

1. **Image Processing (OCR)** → `ocr_engine.py`
2. **Source Monitoring** → `data_fetcher.py`
3. **Indian Perspective Engine** → `analyzer.py`
4. **Recommendations & Output** → `report_pipeline.py`

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python report_pipeline.py
```

## Inputs

- Place your screenshot as `portfolio.png` in this project directory.
- Optional API keys:
  - `X_BEARER_TOKEN`
  - `NEWS_API_KEY`

## Reliability Guards

- OCR errors and low-confidence conditions are logged to `error_log.txt`.
- API fetching uses exponential backoff for rate limits (HTTP 429).
- If data is insufficient, output includes:
  - `Data Deficiency Warning`

## Constraint Compliance

- No price targets are generated.
- Action output is strictly `Buy/Hold/Sell` (with divergence annotation where applicable).


## Phase 2.1 Hardening

Added:
- `.env` driven configuration (`config.py`)
- Unit tests (`tests/`) using `pytest`
- Scheduler sample (`scheduler_example.cron`)
- Multi-format report exports (`.md`, `.csv`, `.json`)
- Telegram digest formatter (`telegram_formatter.py`)

## Testing

```bash
pytest -q
```

## Environment file

```bash
cp .env.example .env
# then fill API keys as needed
```
