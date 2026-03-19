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
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "sentiment", "global_context", "action", "warning"])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def export_rows_json(rows: Sequence[AnalysisRow], path: Path) -> None:
    """Export analysis rows to JSON.

    Args:
        rows: Rows to serialize.
        path: Output JSON path.
    """
    data = [asdict(r) for r in rows]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
