# Bharat Market Pulse — Key Learnings

## What worked well
- Use a **layered extraction strategy** for portfolio screenshots:
  1) Agent JSON holdings (most reliable)
  2) LLM extraction
  3) OCR fallback
- Add **error logging + confidence checks** (`error_log.txt`) to avoid silent failures.
- Handle API instability with **exponential backoff** (especially HTTP 429 rate limits).
- Keep recommendations constrained and auditable:
  - No price targets
  - Actions limited to `Buy / Hold / Sell`

## Architecture lessons
- Splitting pipeline into focused modules improves reliability and maintenance:
  - OCR: `ocr_engine.py`
  - Data collection: `data_fetcher.py`
  - Analysis: `analyzer.py`
  - Report assembly: `report_pipeline.py`
- Configuration via `.env` + `config.py` keeps secrets out of code and supports safe deployment.
- Multi-format exports (`.md`, `.csv`, `.json`) improve downstream reuse.

## Analysis quality improvements
- Source weighting is critical:
  - Prioritize official/trusted outlets
  - Downweight social signals
  - Filter by trusted domains where possible
- Add **global context** (Fed, inflation, oil, USD) before stock-level decisions.
- Improve interpretability with:
  - Per-ticker citations
  - Confidence scores
  - Plain-language summary section

## Robustness and scaling
- Multi-screenshot ingestion (`MARKET_REPORT_IMAGE_PATHS`) helps with larger portfolios and varied layouts.
- A lightweight debate/simulation layer (swarm + sanity checks) can stress-test action bias before final output.
- Scheduled runs (pre-open and post-close) reduce manual load and keep updates consistent.

## Practical operational guidance
- Always include a **Data Deficiency Warning** when evidence is thin.
- Keep report sections stable for readability:
  1. Quick Read
  2. Important Global Events
  3. Portfolio Action Table
  4. In Simple Words
  5. Sources
- Pair automation with tests (`pytest`) and clear examples (`.env.example`, cron sample).
