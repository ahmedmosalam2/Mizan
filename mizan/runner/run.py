"""
Runner — Executes a single framework against Ramadan benchmark probes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console

from mizan.adapters.base import ALL_PROBES, BenchmarkResult, ProbeId
from mizan.adapters.registry import get_adapter
from mizan.scenario.loader import build_scenario
from mizan.scoring.evaluator import BenchmarkEvaluator, EvaluationReport


async def run_framework(
    framework_name: str,
    probes: Optional[List[ProbeId]] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    results_dir: str = "results",
    verbose: bool = False,
) -> EvaluationReport:
    console = Console(highlight=False)
    console.print(f"[bold cyan]>> Initializing Ramadan Campaign Benchmark for:[/] [bold magenta]{framework_name.upper()}[/]")

    scenario = build_scenario(probes=probes or list(ALL_PROBES), llm_config=llm_config)
    adapter = get_adapter(framework_name)

    await adapter.setup(scenario.llm_config)

    console.print(f"Running {len(scenario.probes_to_run)} dimension probes...")
    result: BenchmarkResult = await adapter.run(scenario)

    await adapter.teardown()

    # Evaluate against ground truth
    evaluator = BenchmarkEvaluator()
    report = evaluator.evaluate(result, scenario.ground_truth)

    # Save to JSON
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"{framework_name}_{timestamp_str}.json"

    payload = {
        "framework": framework_name,
        "run_id": result.run_id,
        "total_score": report.total_score,
        "dimension_scores": {
            k: {
                "score": v.score,
                "weight": v.weight,
                "sub_scores": v.sub_scores,
            }
            for k, v in report.dimension_scores.items()
        },
        "total_duration_ms": report.total_duration_ms,
        "total_tokens": report.total_tokens,
        "evaluated_at": report.evaluated_at,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    console.print(f"[green][+] Completed {framework_name.upper()} | Score: {report.total_score:.2f} / 10 | Saved -> {out_file}[/]")
    return report
