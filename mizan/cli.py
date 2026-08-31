"""
Mizan CLI — Command Line Interface for running AI multi-agent benchmarks.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional
import typer
from rich.console import Console

from mizan.adapters.registry import list_available_frameworks
from mizan.runner.matrix import run_matrix
from mizan.runner.run import run_framework

app = typer.Typer(
    name="mizan",
    help="🏆 Mizan — Omnichannel Ramadan Campaign Multi-Agent Benchmark (20 Frameworks)",
    add_completion=False,
)
console = Console()


@app.command("run")
def run_single(
    framework: str = typer.Option(..., "--framework", "-f", help="Framework to benchmark (e.g. crewai, langgraph, native, autogen)"),
    probes: Optional[List[str]] = typer.Option(None, "--probe", "-p", help="Specific probes to run (orchestration, tool_use, safety, hitl, memory, multimodal)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full agent execution trace"),
):
    """Run benchmark probes against a single framework."""
    asyncio.run(run_framework(framework_name=framework, probes=probes, verbose=verbose))


@app.command("matrix")
def run_all(
    frameworks: Optional[List[str]] = typer.Option(None, "--frameworks", "-f", help="List of frameworks to benchmark"),
    report: str = typer.Option("reports/LEADERBOARD.md", "--report", "-r", help="Output markdown report path"),
):
    """Run full benchmark matrix across multiple frameworks and print leaderboard."""
    fws = frameworks or ["native", "crewai", "langgraph", "autogen"]
    asyncio.run(run_matrix(frameworks=fws, report_file=report))


@app.command("list-frameworks")
def list_fws():
    """List all supported and registered framework adapters."""
    fws = list_available_frameworks()
    console.print("\n[bold cyan]Available Framework Adapters in Mizan:[reset]")
    for fw in fws:
        console.print(f"  • [bold green]{fw}[/]")
    console.print()


if __name__ == "__main__":
    app()
