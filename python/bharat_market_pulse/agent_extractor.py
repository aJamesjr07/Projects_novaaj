"""Load holdings extracted by the OpenClaw agent into a JSON file.

This is a no-API path: the assistant can parse screenshot in-chat and save
structured holdings into this file for the pipeline to consume.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ocr_engine import Holding


def load_agent_extracted_holdings(file_path: str) -> List[Holding]:
    """Load holdings from local JSON file.

    Accepted schema:
    {
      "holdings": [
        {"ticker": "BEL", "quantity": 12, "confidence": 0.92}
      ]
    }
    Or raw list of objects.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("holdings", []) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []

    out: List[Holding] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker", "")).strip().upper().replace(" ", "")
        if not ticker:
            continue
        try:
            qty = int(float(row.get("quantity", 0)))
            conf = float(row.get("confidence", 0.85))
        except Exception:
            continue
        if qty <= 0:
            continue
        out.append(Holding(ticker=ticker, quantity=qty, confidence=max(0.0, min(conf, 1.0))))

    # de-dup keep highest confidence
    best: dict[str, Holding] = {}
    for h in out:
        prev = best.get(h.ticker)
        if prev is None or h.confidence > prev.confidence:
            best[h.ticker] = h

    return list(best.values())
