"""
run_matrix.py — Run all scenarios against all (or selected) frameworks.

Usage:
    python runner/run_matrix.py                        # all frameworks × all scenarios
    python runner/run_matrix.py --framework crewai     # one framework
    python runner/run_matrix.py --category safety      # one category
    python runner/run_matrix.py --repeat 3             # run each scenario 3 times
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from frameworks.registry import list_frameworks, get_adapter
from runner.run_scenario import run_scenario
from scenarios.loader import list_scenarios
from shared.llm_config import get_config
from shared.scoring.scorer import BenchmarkScorer, FrameworkScore


async def run_matrix(
    frameworks: list[str] | None = None,
    categories: list[str] | None = None,
    repeat: int = 1,
) -> dict:
    """Run the full benchmark matrix."""

    config = get_config()
    all_frameworks = frameworks or list(list_frameworks().keys())
    all_scenarios  = list_scenarios()

    if categories:
        all_scenarios = [s for s in all_scenarios
                         if any(cat in s for cat in categories)]

    total = len(all_frameworks) * len(all_scenarios) * repeat
    print(f"\n🏁 Mizan Benchmark Matrix")
    print(f"   Frameworks : {all_frameworks}")
    print(f"   Scenarios  : {len(all_scenarios)}")
    print(f"   Repeats    : {repeat}")
    print(f"   Total runs : {total}")
    print(f"   Model      : {config.llm.model}")
    print(f"   Started at : {datetime.now().isoformat()}\n")

    all_results: dict[str, list[dict]] = {fw: [] for fw in all_frameworks}
    run_n = 0

    for framework_id in all_frameworks:
        for scenario_id in all_scenarios:
            for run_i in range(repeat):
                run_n += 1
                print(f"[{run_n}/{total}] {framework_id} × {scenario_id} (run {run_i+1}/{repeat})")
                try:
                    result = await run_scenario(framework_id, scenario_id)
                    all_results[framework_id].append(result)
                except Exception as exc:
                    print(f"  ❌ FAILED: {exc}")
                    all_results[framework_id].append({
                        "framework": framework_id,
                        "scenario": scenario_id,
                        "status": "error",
                        "error": str(exc),
                    })

    # Save matrix results
    output_dir = Path("results/runs")
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / f"matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(matrix_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Matrix complete → {matrix_path}")
    _print_summary(all_results, all_scenarios)
    return all_results


def _print_summary(results: dict, scenarios: list):
    """Print a quick leaderboard to the console."""
    print("\n" + "="*60)
    print("  MIZAN LEADERBOARD (quick summary)")
    print("="*60)
    print(f"{'Framework':<20} {'Completed':<12} {'Failed':<10} {'Avg ms':<12}")
    print("-"*60)

    for fw, runs in sorted(results.items()):
        completed = sum(1 for r in runs if r.get("status") == "completed")
        failed    = sum(1 for r in runs if r.get("status") != "completed")
        avg_ms    = (
            sum(r.get("duration_ms", 0) for r in runs) / len(runs)
            if runs else 0
        )
        print(f"{fw:<20} {completed:<12} {failed:<10} {avg_ms:<12.0f}")

    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Run the full Mizan benchmark matrix")
    parser.add_argument("--framework", "-f", nargs="+", help="Framework IDs to include")
    parser.add_argument("--category",  "-c", nargs="+",
                        choices=["orchestration", "tools", "safety", "hitl", "memory", "multimodal"])
    parser.add_argument("--repeat",    "-r", type=int, default=1, help="Repeat count per scenario")
    args = parser.parse_args()

    asyncio.run(run_matrix(
        frameworks=args.framework,
        categories=args.category,
        repeat=args.repeat,
    ))


if __name__ == "__main__":
    main()
