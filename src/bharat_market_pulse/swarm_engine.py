"""Phase S2: lightweight 4-agent market debate engine.

Simulates a compact MAD-style debate across four archetypes:
- FII macro
- DII fundamental
- Retail momentum
- Risk manager
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from .news_collector import SeedNews
from .sanity_check import SanityResult, apply_volatility_guard


LOG_PATH = Path(__file__).resolve().parent / "logs" / "system_errors.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


@dataclass(frozen=True)
class Agent:
    name: str
    archetype: str
    bias: float  # baseline directional preference [-1,1]
    reactivity: float  # how strongly agent updates each round


@dataclass(frozen=True)
class SwarmOutcome:
    consensus_score: float  # [-1,1]
    consensus_label: str
    confidence_1_to_10: float
    rounds: int
    notes: List[str]
    sanity: SanityResult


def default_four_agents() -> List[Agent]:
    """Return default 4-agent setup."""
    return [
        Agent("FII Macro", "fii", bias=-0.05, reactivity=0.75),
        Agent("DII Fundamental", "dii", bias=0.10, reactivity=0.55),
        Agent("Retail Momentum", "retail", bias=0.15, reactivity=0.90),
        Agent("Risk Manager", "risk", bias=-0.10, reactivity=0.80),
    ]


def _seed_event_score(seed: SeedNews) -> float:
    t = seed.title.lower()
    score = 0.0
    if any(k in t for k in {"rate hike", "repo hike", "inflation", "selloff", "downgrade"}):
        score -= 0.45
    if any(k in t for k in {"rate cut", "order win", "earnings beat", "upgrade", "capex boost"}):
        score += 0.45
    if any(k in t for k in {"policy", "rbi", "fed", "crude", "yields"}):
        score += -0.1 if score < 0 else 0.1
    return max(-1.0, min(1.0, score))


def run_swarm_debate(
    seed_news: Sequence[SeedNews],
    rounds: int = 3,
    baseline_volatility: float = 0.25,
) -> SwarmOutcome:
    """Run multi-agent debate with 4 agents and aggregate consensus."""
    agents = default_four_agents()
    if not seed_news:
        sanity = apply_volatility_guard(0.0, baseline_volatility, catalyst_strength=0.0)
        return SwarmOutcome(0.0, "Neutral", 3.0, 0, ["No seed news provided"], sanity)

    seed_scores = [_seed_event_score(s) for s in seed_news[:6]]
    macro_pulse = sum(seed_scores) / max(1, len(seed_scores))

    states = [a.bias for a in agents]
    notes: List[str] = []

    for r in range(rounds):
        round_avg = sum(states) / len(states)
        new_states: List[float] = []
        for i, agent in enumerate(agents):
            influence = 0.55 * macro_pulse + 0.45 * round_avg
            updated = states[i] + agent.reactivity * 0.35 * (influence - states[i])
            updated = max(-1.0, min(1.0, updated))
            new_states.append(updated)
        states = new_states
        notes.append(f"Round {r + 1}: avg sentiment={sum(states) / len(states):.2f}")

    raw_consensus = sum(states) / len(states)
    catalyst_strength = min(1.0, abs(macro_pulse) + 0.2)
    sanity = apply_volatility_guard(raw_consensus, baseline_volatility, catalyst_strength)
    consensus = sanity.adjusted_score

    if consensus >= 0.20:
        label = "Bullish"
    elif consensus <= -0.20:
        label = "Bearish"
    else:
        label = "Neutral"

    disagreement = max(states) - min(states)
    confidence = max(1.0, min(10.0, 8.0 - 4.0 * disagreement + 2.0 * abs(consensus)))

    logging.info(
        "Swarm completed: raw=%.3f adjusted=%.3f label=%s confidence=%.2f",
        raw_consensus,
        consensus,
        label,
        confidence,
    )

    return SwarmOutcome(
        consensus_score=round(consensus, 3),
        consensus_label=label,
        confidence_1_to_10=round(confidence, 2),
        rounds=rounds,
        notes=notes,
        sanity=sanity,
    )


if __name__ == "__main__":
    sample = [
        SeedNews(
            title="RBI raises repo rate by 25 bps",
            source="sample",
            url="https://example.com",
            tag="policy",
            reliability=0.9,
        )
    ]
    outcome = run_swarm_debate(sample)
    print(outcome)
