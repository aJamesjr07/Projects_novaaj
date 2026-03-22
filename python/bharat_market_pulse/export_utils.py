"""Export utilities for markdown, CSV, and JSON report artifacts."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from analyzer import AnalysisRow


def ensure_output_dir(path: Path) -> None:
    """Ensure output directory exists.

    Args:
        path: Target directory path.
    """
    path.mkdir(parents=True, exist_ok=True)


def export_rows_csv(rows: Sequence[AnalysisRow], path: Path) -> None:
    """Export analysis rows to CSV.

    Args:
        rows: Rows to serialize.
        path: Output CSV path.
    """
    fieldnames = [
        "ticker",
        "sentiment",
        "global_context",
        "action",
        "confidence",
        "layman_summary",
        "citations",
        "warning",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload = asdict(row)
            payload["citations"] = " | ".join(payload.get("citations", []))
            writer.writerow(payload)


def export_rows_json(rows: Sequence[AnalysisRow], path: Path) -> None:
    """Export analysis rows to JSON.

    Args:
        rows: Rows to serialize.
        path: Output JSON path.
    """
    data = [asdict(r) for r in rows]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
