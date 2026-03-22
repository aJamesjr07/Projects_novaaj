"""Run Phase S1 + S2 sandbox (news collection + 4-agent swarm debate)."""

from __future__ import annotations

from .news_collector import collect_seed_news
from .swarm_engine import run_swarm_debate


def main() -> None:
    seeds = collect_seed_news(limit=10)
    outcome = run_swarm_debate(seeds, rounds=3, baseline_volatility=0.25)

    print("# Predictive Sandbox (Phase S1 + S2)")
    print(f"Seed items: {len(seeds)}")
    print(f"Consensus: {outcome.consensus_label} ({outcome.consensus_score:+.2f})")
    print(f"Confidence (1-10): {outcome.confidence_1_to_10}")
    print(f"Sanity: {outcome.sanity.reason}")
    if seeds:
        print("\nTop seed headlines:")
        for s in seeds[:5]:
            print(f"- [{s.tag}] {s.title} ({s.source})")


if __name__ == "__main__":
    main()
