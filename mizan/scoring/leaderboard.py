"""
Leaderboard Generator & Summary Reporter for Mizan Benchmark.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.table import Table

from mizan.scoring.evaluator import EvaluationReport

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"


class Leaderboard:
    """Renders competitive benchmark leaderboards across frameworks."""

    @classmethod
    def display(cls, reports: List[EvaluationReport]) -> None:
        console = Console(highlight=False)
        table = Table(title="Mizan Benchmark — 20 Framework Evaluation Matrix (Ramadan Campaign)", header_style="bold magenta")

        table.add_column("Rank", justify="center", style="bold")
        table.add_column("Framework", justify="left", style="cyan")
        table.add_column("Total Score", justify="right", style="bold green")
        table.add_column("Orch (20%)", justify="right")
        table.add_column("Tools (15%)", justify="right")
        table.add_column("Safety (15%)", justify="right")
        table.add_column("HITL (15%)", justify="right")
        table.add_column("Memory (10%)", justify="right")
        table.add_column("Obs (10%)", justify="right")
        table.add_column("Vision (15%)", justify="right")
        table.add_column("Latency", justify="right", style="dim")

        sorted_reports = sorted(reports, key=lambda r: r.total_score, reverse=True)

        for rank, r in enumerate(sorted_reports, 1):
            d = r.dimension_scores
            table.add_row(
                f"#{rank}",
                r.framework_name,
                f"{r.total_score:.2f} / 10",
                f"{d.get('orchestration', type('', (), {'score': 0})()).score:.1f}",
                f"{d.get('tool_use', type('', (), {'score': 0})()).score:.1f}",
                f"{d.get('safety', type('', (), {'score': 0})()).score:.1f}",
                f"{d.get('human_in_the_loop', type('', (), {'score': 0})()).score:.1f}",
                f"{d.get('memory', type('', (), {'score': 0})()).score:.1f}",
                f"{d.get('observability', type('', (), {'score': 0})()).score:.1f}",
                f"{d.get('multimodal', type('', (), {'score': 0})()).score:.1f}",
                f"{r.total_duration_ms / 1000:.1f}s",
            )

        console.print()
        console.print(table)
        console.print()

    @classmethod
    def save_markdown_report(cls, reports: List[EvaluationReport], file_path: str = "reports/LEADERBOARD.md") -> None:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        sorted_reports = sorted(reports, key=lambda r: r.total_score, reverse=True)

        lines = [
            "# Mizan AI Agentic Framework Benchmark — Official Leaderboard",
            "",
            "**Use Case**: Omnichannel Ramadan Campaign & Customer Engagement Orchestrator (KSA + Egypt)",
            "",
            "| Rank | Framework | Total Score (0-10) | Orchestration (20%) | Tool Use (15%) | Safety (15%) | HITL (15%) | Memory (10%) | Observability (10%) | Multimodal (15%) | Duration |",
            "|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for rank, r in enumerate(sorted_reports, 1):
            d = r.dimension_scores
            lines.append(
                f"| #{rank} | **{r.framework_name}** | **{r.total_score:.2f}** | "
                f"{d.get('orchestration', type('', (), {'score': 0})()).score:.1f} | "
                f"{d.get('tool_use', type('', (), {'score': 0})()).score:.1f} | "
                f"{d.get('safety', type('', (), {'score': 0})()).score:.1f} | "
                f"{d.get('human_in_the_loop', type('', (), {'score': 0})()).score:.1f} | "
                f"{d.get('memory', type('', (), {'score': 0})()).score:.1f} | "
                f"{d.get('observability', type('', (), {'score': 0})()).score:.1f} | "
                f"{d.get('multimodal', type('', (), {'score': 0})()).score:.1f} | "
                f"{r.total_duration_ms / 1000:.1f}s |"
            )

        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
