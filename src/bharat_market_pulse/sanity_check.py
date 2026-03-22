"""Phase S1: guardrails for simulation outputs.

Ensures simulated scores stay within reasonable bounds unless catalyst strength is high.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SanityResult:
    """Sanity check output."""

    passed: bool
    adjusted_score: float
    reason: str


def apply_volatility_guard(
    raw_score: float,
    baseline_volatility: float,
    catalyst_strength: float,
    max_deviation_multiple: float = 1.5,
) -> SanityResult:
    """Clamp overly aggressive predictions.

    Args:
        raw_score: Simulated directional score in [-1, 1].
        baseline_volatility: Approx historical volatility proxy (0-1 scale).
        catalyst_strength: Strength of catalyst (0-1).
        max_deviation_multiple: Maximum tolerated multiple of baseline risk.

    Returns:
        SanityResult with adjusted score when needed.
    """
    limit = min(1.0, baseline_volatility * max_deviation_multiple)

    # Allow larger swings only when catalyst is very strong.
    if catalyst_strength >= 0.85:
        return SanityResult(
            True, max(-1.0, min(1.0, raw_score)), "Strong catalyst override"
        )

    if abs(raw_score) <= limit:
        return SanityResult(True, raw_score, "Within volatility guard")

    adjusted = limit if raw_score > 0 else -limit
    return SanityResult(False, adjusted, "Clamped by volatility guard")
