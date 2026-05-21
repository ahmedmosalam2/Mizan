"""
Benchmark Runner — Executes all scenarios on all framework adapters.

Usage:
    python -m benchmarks.runner --frameworks crewai langgraph --scenarios all
    python -m benchmarks.runner --all
"""

import asyncio
import json
import time
import logging
import importlib
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter,
    ScenarioResult,
    AgentSpec,
    ToolSpec,
)
from benchmarks.scenarios.test_data import (
    AGENT_SPECS,
    CAMPAIGN_BRIEF,
    CONTENT_GENERATION_TASK,
    PII_TEST_TEXTS,
    EXPECTED_PII_DETECTIONS,
    BUDGET_REALLOCATION_REQUEST,
    SIMULATED_APPROVALS,
    APPROVAL_RULES,
    CONVERSATION_HISTORY,
    MEMORY_FOLLOW_UP,
    EXPECTED_RECALL,
    DEPLOYMENT_TASK,
    MULTIMODAL_TASK,
    FRAMEWORKS_REGISTRY,
)
from benchmarks.scoring.scorer import BenchmarkScorer, FrameworkScore
from benchmarks.reporting.report_generator import generate_report

logger = logging.getLogger("mizan.runner")

RESULTS_DIR = Path("benchmark_results")


def _load_adapter(framework_id: str) -> Optional[BaseFrameworkAdapter]:
    """Dynamically load a framework adapter by ID."""
    try:
        module = importlib.import_module(f"benchmarks.adapters.{framework_id}_adapter")
        # Convention: class name is {FrameworkId}Adapter with CamelCase
        class_name = "".join(w.capitalize() for w in framework_id.split("_")) + "Adapter"
        adapter_class = getattr(module, class_name)
        return adapter_class()
    except (ImportError, AttributeError) as e:
        print(f"  [!] Could not load adapter for '{framework_id}': {e}")
        return None


def _build_agent_specs() -> List[AgentSpec]:
    """Convert test data agent dicts to AgentSpec objects."""
    return [
        AgentSpec(
            name=spec["name"],
            role=spec["role"],
            goal=spec["goal"],
            backstory=spec["backstory"],
            can_delegate=spec.get("can_delegate", False),
        )
        for spec in AGENT_SPECS
    ]


class BenchmarkRunner:
    """Runs benchmark scenarios on framework adapters and collects results."""

    def __init__(self, llm_config: Optional[Dict] = None):
        self.llm_config = llm_config or {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key": "",  # Set from env
        }
        self.scorer = BenchmarkScorer()
        self.all_results: Dict[str, Dict[str, ScenarioResult]] = {}
        self.all_scores: List[FrameworkScore] = []

    async def run_single_framework(
        self,
        framework_id: str,
        scenarios: Optional[List[str]] = None,
    ) -> Dict[str, ScenarioResult]:
        """Run all (or selected) scenarios on a single framework."""
        print(f"\n{'='*60}")
        print(f"  BENCHMARKING: {framework_id}")
        print(f"{'='*60}")

        adapter = _load_adapter(framework_id)
        if not adapter:
            return {}

        # Setup
        try:
            await adapter.setup(self.llm_config)
        except Exception as e:
            print(f"  [X] Setup failed: {e}")
            return {}

        # Define scenario runners
        scenario_runners = {
            "campaign_planning": self._run_orchestration,
            "content_generation": self._run_tool_use,
            "pii_scan": self._run_safety,
            "budget_approval": self._run_hitl,
            "cross_session_chat": self._run_memory,
            "channel_deploy": self._run_observability,
            "multimodal_ad": self._run_multimodal,
        }

        if scenarios is None:
            scenarios = list(scenario_runners.keys())

        results = {}
        for scenario_id in scenarios:
            runner_fn = scenario_runners.get(scenario_id)
            if not runner_fn:
                print(f"  [?] Unknown scenario: {scenario_id}")
                continue

            print(f"\n  --- Scenario: {scenario_id} ---")
            adapter.reset_metrics()

            start = time.time()
            try:
                result = await runner_fn(adapter)
                result.total_duration_ms = (time.time() - start) * 1000
                result.started_at = datetime.now().isoformat()
                result.finished_at = datetime.now().isoformat()
                results[scenario_id] = result
                print(f"  [+] {scenario_id}: {result.status} ({result.total_duration_ms:.0f}ms)")
            except Exception as e:
                result = ScenarioResult(
                    scenario_id=scenario_id,
                    framework_name=framework_id,
                    status="failed",
                    error=str(e),
                    total_duration_ms=(time.time() - start) * 1000,
                )
                results[scenario_id] = result
                print(f"  [X] {scenario_id}: FAILED — {e}")

        # Teardown
        try:
            await adapter.teardown()
        except Exception:
            pass

        self.all_results[framework_id] = results
        return results

    async def run_all_frameworks(
        self,
        framework_ids: Optional[List[str]] = None,
        scenarios: Optional[List[str]] = None,
    ) -> Dict[str, FrameworkScore]:
        """Run benchmark on all (or selected) frameworks."""
        if framework_ids is None:
            framework_ids = [fw["id"] for fw in FRAMEWORKS_REGISTRY]

        print(f"\n{'#'*60}")
        print(f"  MIZAN BENCHMARK — {len(framework_ids)} frameworks x {len(scenarios or ['all'])} scenarios")
        print(f"{'#'*60}")

        for fw_id in framework_ids:
            results = await self.run_single_framework(fw_id, scenarios)

            if results:
                score = self.scorer.score_framework(fw_id, results)
                self.all_scores.append(score)

        # Generate comparison
        if self.all_scores:
            comparison = self.scorer.compare_frameworks(self.all_scores)
            self._save_results(comparison)
            self._print_leaderboard(comparison)
            return comparison

        return {}

    # ═══════════════════════════════════════════════════════════════
    # Individual scenario runners
    # ═══════════════════════════════════════════════════════════════

    async def _run_orchestration(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 1: Campaign Planning — tests orchestration."""
        agent_specs = _build_agent_specs()
        return await adapter.run_orchestration(
            agent_specs=agent_specs,
            task=CAMPAIGN_BRIEF,
            orchestration_mode="hierarchical",
        )

    async def _run_tool_use(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 2: Content Generation — tests tool use / RAG."""
        agent_specs = [
            AgentSpec(
                name="ContentArchitect",
                role="Content Generator",
                goal=CONTENT_GENERATION_TASK["goal"],
                backstory=AGENT_SPECS[1]["backstory"],
            ),
        ]

        # Create a mock RAG tool
        def search_catalog(query: str) -> str:
            """Search the product catalog."""
            from benchmarks.scenarios.test_data import PRODUCT_CATALOG
            results = [p for p in PRODUCT_CATALOG if query.lower() in p["name_en"].lower() or query in p["name_ar"]]
            return json.dumps(results[:3], ensure_ascii=False) if results else "No products found"

        tools = [
            ToolSpec(
                name="search_catalog",
                description="Search the product catalog by name or keyword",
                function=search_catalog,
                parameters={"query": {"type": "string", "description": "Search query"}},
            ),
        ]

        return await adapter.run_with_tools(
            agent_specs=agent_specs,
            task=CONTENT_GENERATION_TASK,
            tools=tools,
        )

    async def _run_safety(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 3: PII Scan — tests safety & privacy."""
        return await adapter.run_safety_check(
            text_with_pii=PII_TEST_TEXTS["saudi_text"] + "\n\n" + PII_TEST_TEXTS["egyptian_text"],
            pii_types=["saudi_national_id", "egyptian_national_id", "phone_numbers", "email_addresses", "person_names"],
            jurisdiction="both",
        )

    async def _run_hitl(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 4: Budget Approval — tests human-in-the-loop."""
        agent_specs = [
            AgentSpec(
                name="AnalyticsAgent",
                role="Budget Optimizer",
                goal="Analyze channel performance and recommend budget reallocation.",
                backstory=AGENT_SPECS[3]["backstory"],
            ),
            AgentSpec(
                name="CampaignCommander",
                role="Approval Coordinator",
                goal="Coordinate budget reallocation approval with marketing manager.",
                backstory=AGENT_SPECS[0]["backstory"],
            ),
        ]

        return await adapter.run_with_approval(
            agent_specs=agent_specs,
            task=BUDGET_REALLOCATION_REQUEST,
            approval_rules=APPROVAL_RULES,
            simulated_approvals=SIMULATED_APPROVALS,
        )

    async def _run_memory(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 5: Cross-Session Chat — tests memory."""
        return await adapter.run_with_memory(
            conversation_history=CONVERSATION_HISTORY,
            follow_up_query=CONVERSATION_HISTORY[1]["messages"][0]["content"],
            expected_recall=EXPECTED_RECALL,
        )

    async def _run_observability(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 6: Channel Deploy with Failures — tests observability."""
        agent_specs = [
            AgentSpec(
                name="ChannelDeployer",
                role="Campaign Deployer",
                goal="Deploy campaign across all channels, handle failures with retry and fallback.",
                backstory=AGENT_SPECS[2]["backstory"],
            ),
        ]

        inject_failure = {
            "channel": "snapchat",
            "error_type": "API_RATE_LIMIT",
            "retry_success_after": 2,
        }

        return await adapter.run_with_tracing(
            agent_specs=agent_specs,
            task=DEPLOYMENT_TASK,
            inject_failure=inject_failure,
        )

    async def _run_multimodal(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 7: Product Image → Ad Copy — tests multimodal."""
        return await adapter.run_multimodal(
            image_path=None,  # Will use product URL from task
            document_path=None,
            task=MULTIMODAL_TASK,
        )

    # ═══════════════════════════════════════════════════════════════
    # Output
    # ═══════════════════════════════════════════════════════════════

    def _save_results(self, comparison: Dict):
        """Save results to JSON + HTML report."""
        RESULTS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON
        json_path = RESULTS_DIR / f"benchmark_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n  📄 JSON saved:  {json_path}")

        # HTML Report
        try:
            html_path = generate_report(
                comparison,
                output_dir=str(RESULTS_DIR),
                filename_prefix=timestamp,
            )
            print(f"  📊 HTML report: {html_path}")
        except Exception as e:
            logger.warning(f"HTML report generation failed: {e}")

    def _print_leaderboard(self, comparison: Dict):
        """Print a formatted leaderboard to console."""
        print(f"\n{'='*80}")
        print(f"  ⚖️  MIZAN BENCHMARK LEADERBOARD")
        print(f"{'='*80}")
        print(f"  {'Rank':<5} {'Framework':<20} {'Score':<8} {'Orch':<6} {'Tools':<6} "
              f"{'Safety':<7} {'HITL':<6} {'Mem':<6} {'Obs':<6} {'Multi':<6}")
        print(f"  {'-'*74}")

        medals = {1: '🥇', 2: '🥈', 3: '🥉'}
        for entry in comparison["ranking"]:
            dims = entry["dimensions"]
            medal = medals.get(entry['rank'], f"  {entry['rank']}")
            print(
                f"  {medal:<5} {entry['framework']:<20} "
                f"{entry['total_score']:<8.2f} "
                f"{dims.get('orchestration', 0):<6.1f} "
                f"{dims.get('tool_use', 0):<6.1f} "
                f"{dims.get('safety', 0):<7.1f} "
                f"{dims.get('human_in_the_loop', 0):<6.1f} "
                f"{dims.get('memory', 0):<6.1f} "
                f"{dims.get('observability', 0):<6.1f} "
                f"{dims.get('multimodal', 0):<6.1f}"
            )

        print(f"\n  🏆 Best per dimension:")
        for dim, info in comparison.get("best_per_dimension", {}).items():
            print(f"    {dim:<25} {info['framework']:<20} ({info['score']}/10)")


# ═══════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════

async def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Mizan Benchmark Runner")
    parser.add_argument("--frameworks", nargs="+", default=None,
                        help="Framework IDs to benchmark (default: all available)")
    parser.add_argument("--scenarios", nargs="+", default=None,
                        help="Scenario IDs to run (default: all)")
    parser.add_argument("--llm-provider", default="groq", help="LLM provider")
    parser.add_argument("--llm-model", default="llama-3.3-70b-versatile", help="LLM model")
    args = parser.parse_args()

    llm_config = {
        "provider": args.llm_provider,
        "model": args.llm_model,
        "api_key": os.getenv("GROQ_API_KEY", ""),
    }

    runner = BenchmarkRunner(llm_config=llm_config)
    await runner.run_all_frameworks(
        framework_ids=args.frameworks,
        scenarios=args.scenarios,
    )


if __name__ == "__main__":
    asyncio.run(main())
