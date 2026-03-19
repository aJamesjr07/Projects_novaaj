# Bharat Market Pulse

A self-documenting Python pipeline to convert a portfolio screenshot into a daily **Bharat Market Pulse report**.

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

## Phase 3.0 Upgrade

Added:
- Trusted source weighting (official/news/social reliability scoring)
- Global events section (Fed/inflation/oil/dollar style context)
- Citation-aware analysis per ticker
- Confidence score per action row
- Layman-friendly report text (`In Simple Words` section)
- Hybrid screenshot extraction (EasyOCR + optional Tesseract + consensus row parsing)

### Report sections now

1. Quick Read (30 seconds)
2. Important Global Events (and why they matter)
3. Portfolio Action Table (with confidence)
4. In Simple Words (easy explanation)
5. Sources (citations)

## Automation (before open + after close)

Use the provided schedule:

```bash
crontab scheduler_example.cron
```

This runs the report on weekdays:
- 9:00 AM IST (before market open)
- 3:45 PM IST (after market close)

## Testing

```bash
pytest -q
```

## Environment file

```bash
cp .env.example .env
# then fill API keys as needed
```
