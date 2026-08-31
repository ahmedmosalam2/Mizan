"""
Matrix Runner — Runs multiple frameworks and outputs comparative leaderboard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from rich.console import Console

from mizan.adapters.base import ProbeId
from mizan.runner.run import run_framework
from mizan.scoring.evaluator import EvaluationReport
from mizan.scoring.leaderboard import Leaderboard


async def run_matrix(
    frameworks: List[str],
    probes: Optional[List[ProbeId]] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    results_dir: str = "results",
    report_file: str = "reports/LEADERBOARD.md",
) -> List[EvaluationReport]:
    console = Console(highlight=False)
    console.print(f"[bold yellow]==================================================================[/]")
    console.print(f"[bold yellow]  MIZAN MULTI-FRAMEWORK BENCHMARK MATRIX ({len(frameworks)} Frameworks)[/]")
    console.print(f"[bold yellow]==================================================================[/]\n")

    reports: List[EvaluationReport] = []
    for fw in frameworks:
        try:
            rep = await run_framework(framework_name=fw, probes=probes, llm_config=llm_config, results_dir=results_dir)
            reports.append(rep)
        except Exception as e:
            console.print(f"[bold red][!] Failed running {fw}: {e}[/]")

    # Display Leaderboard
    Leaderboard.display(reports)
    Leaderboard.save_markdown_report(reports, file_path=report_file)

    console.print(f"[bold green][+] Leaderboard report saved to: {report_file}[/]\n")
    return reports
