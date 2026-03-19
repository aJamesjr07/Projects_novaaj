# Phase 3.0 Upgrade Notes

## Objective
Improve report quality using better sources, source citations, global event context, and plain-language summaries.

## Implemented

- Source reliability scoring by source family:
  - official: 0.95
  - news: 0.78
  - twitter: 0.62
  - reddit: 0.52
- Official feed support (SEBI RSS)
- Global event fetch stream (Fed, inflation, oil, dollar via NewsAPI)
- Citation extraction and deduplicated source list in final report
- Confidence score per ticker row
- Layman-friendly summary line per ticker

## User-facing impact

The daily report is now easier to read and more trustworthy because each recommendation has:
- context,
- confidence,
- and explicit source links.

## Next suggested step

Add more official Indian feeds (RBI/NSE/BSE) and a strict citation rule:
- if <2 trusted citations, downgrade action to `Hold` and show warning.
