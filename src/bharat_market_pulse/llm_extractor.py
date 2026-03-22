"""LLM-first screenshot extractor for Bharat Market Pulse.

Uses a vision-capable model (OpenAI-compatible API) to parse holdings from a
portfolio screenshot into structured rows, then maps rows to `Holding` objects.
If config/API is missing or parsing fails, callers should fall back to OCR.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import requests

from .ocr_engine import Holding


@dataclass(frozen=True)
class LLMExtractorSettings:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: int = 45


def _to_data_url(image_path: Path) -> str:
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _normalize_ticker(raw: str) -> str:
    t = (raw or "").strip().upper().replace(" ", "")
    alias = {
        "NIPPONINDIAGOLDBEES": "GOLDBEES",
        "BHARATELECTRONICS": "BEL",
        "HINDUSTANCOPPER": "HINDCOPPER",
        "PARASDEFENCE": "PARAS",
    }
    return alias.get(t, t)


def _parse_rows(content: str) -> List[Holding]:
    """Parse JSON payload from model into Holding list."""
    payload = json.loads(content)
    rows = payload.get("holdings", []) if isinstance(payload, dict) else payload
    out: List[Holding] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = _normalize_ticker(str(row.get("ticker", "")))
        qty_raw = row.get("quantity", row.get("qty", 0))
        conf_raw = row.get("confidence", 0.7)
        try:
            qty = int(float(qty_raw))
            conf = float(conf_raw)
        except Exception:
            continue
        if not ticker or qty <= 0:
            continue
        out.append(
            Holding(ticker=ticker, quantity=qty, confidence=max(0.0, min(conf, 1.0)))
        )

    # de-dup keep highest confidence
    best: dict[str, Holding] = {}
    for h in out:
        prev = best.get(h.ticker)
        if prev is None or h.confidence > prev.confidence:
            best[h.ticker] = h
    return list(best.values())


def run_llm_extraction(
    image_path: str, settings: LLMExtractorSettings
) -> List[Holding]:
    """Extract holdings from screenshot via vision LLM.

    Raises RuntimeError on API/config/parse failure.
    """
    if not settings.api_key:
        raise RuntimeError("LLM API key not configured")

    path = Path(image_path)
    if not path.exists():
        raise RuntimeError(f"Image not found: {path}")

    prompt = (
        "You are extracting holdings from an Indian brokerage holdings screenshot. "
        "Return ONLY strict JSON with schema: "
        '{"holdings":[{"ticker":string,"quantity":number,"confidence":number}]}. '
        "Rules: include only clear holdings rows; ignore UI words (holdings, shares labels, totals). "
        "Ticker should be NSE-style short symbol if possible (e.g., BEL, HINDCOPPER, GOLDBEES, SILVERBEES, TATAGOLD, TATSILV, HINDALCO, IOC, BPCL, OIL, VEDL, NALCO, LAURUS, PARAS). "
        "Quantity must be units/shares count and positive integer."
    )

    data_url = _to_data_url(path)
    url = settings.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    }

    resp = requests.post(
        url, headers=headers, json=body, timeout=settings.timeout_seconds
    )
    if resp.status_code >= 300:
        raise RuntimeError(
            f"LLM extraction failed: HTTP {resp.status_code} {resp.text[:300]}"
        )

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {data}") from exc

    holdings = _parse_rows(content)
    if not holdings:
        raise RuntimeError("LLM returned no parseable holdings")
    return holdings
