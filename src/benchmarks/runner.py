"""
Benchmark Runner — Executes all scenarios on all framework adapters.

Usage:
    python -m benchmarks.runner --frameworks crewai langgraph --scenarios all
    python -m benchmarks.runner --all
    python -m benchmarks.runner --dry-run            # Validate without running
    python -m benchmarks.runner --mock                # Use mock LLM (no API keys needed)
    python -m benchmarks.runner --timeout 60          # Per-scenario timeout (seconds)
    python -m benchmarks.runner --output-format json   # json | html | markdown | all
"""

import asyncio
import json
import time
import logging
import importlib
import sys
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from benchmarks.models import (
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

# ═══════════════════════════════════════════════════════════════
# Structured Logging Setup
# ═══════════════════════════════════════════════════════════════

logger = logging.getLogger("mizan.runner")

# CLI-facing logger — user-visible output
cli_logger = logging.getLogger("mizan.cli")


def _setup_logging(verbose: bool = False, quiet: bool = False):
    """Configure structured logging for runner and CLI output."""
    log_level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)

    # Internal engine logger — structured for debugging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # CLI output handler — clean user-facing messages
    # Force UTF-8 on Windows to avoid cp1252 emoji crashes
    cli_stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
    cli_handler = logging.StreamHandler(cli_stream)
    cli_handler.setFormatter(logging.Formatter("%(message)s"))
    cli_logger.addHandler(cli_handler)
    cli_logger.setLevel(logging.INFO if not quiet else logging.WARNING)
    cli_logger.propagate = False


RESULTS_DIR = Path("benchmark_results")

ALL_SCENARIO_IDS = [
    "campaign_planning",
    "content_generation",
    "pii_scan",
    "budget_approval",
    "cross_session_chat",
    "channel_deploy",
    "multimodal_ad",
]


def _load_adapter(framework_id: str) -> Optional[BaseFrameworkAdapter]:
    """Dynamically load a framework adapter by ID."""
    try:
        import importlib.util
        # Try package structure first (e.g., benchmarks.adapters.crewai)
        if importlib.util.find_spec(f"benchmarks.adapters.{framework_id}"):
            module = importlib.import_module(f"benchmarks.adapters.{framework_id}")
        else:
            module = importlib.import_module(f"benchmarks.adapters.{framework_id}_adapter")
            
        # Convention: class name is {FrameworkId}Adapter with CamelCase
        class_name = "".join(w.capitalize() for w in framework_id.split("_")) + "Adapter"
        adapter_class = getattr(module, class_name)
        return adapter_class()
    except ImportError as e:
        logger.warning("Could not import adapter for '%s': %s", framework_id, e)
        cli_logger.info("  [!] Could not load adapter for '%s': %s", framework_id, e)
        return None
    except AttributeError as e:
        logger.error("Adapter class not found for '%s': %s", framework_id, e)
        cli_logger.info("  [!] Adapter class missing for '%s': %s", framework_id, e)
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

    def __init__(
        self,
        llm_config: Optional[Dict] = None,
        timeout_seconds: float = 120.0,
        dry_run: bool = False,
        output_format: str = "all",
        campaign_config: Optional[str] = None,
    ):
        self.llm_config = llm_config or {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key": "",  # Set from env
        }
        self.scorer = BenchmarkScorer()
        self.all_results: Dict[str, Dict[str, ScenarioResult]] = {}
        self.all_scores: List[FrameworkScore] = []
        self.timeout_seconds = timeout_seconds
        self.dry_run = dry_run
        self.output_format = output_format

        # Load custom campaign or use defaults from test_data
        if campaign_config:
            self._load_custom_campaign(campaign_config)
        else:
            self._load_default_data()

    def _load_default_data(self):
        """Use the built-in test_data scenarios."""
        self._campaign_brief = CAMPAIGN_BRIEF
        self._content_task = CONTENT_GENERATION_TASK
        self._pii_texts = PII_TEST_TEXTS
        self._budget_request = BUDGET_REALLOCATION_REQUEST
        self._approval_rules = APPROVAL_RULES
        self._simulated_approvals = SIMULATED_APPROVALS
        self._conversation_history = CONVERSATION_HISTORY
        self._expected_recall = EXPECTED_RECALL
        self._deployment_task = DEPLOYMENT_TASK
        self._multimodal_task = MULTIMODAL_TASK

    def _load_custom_campaign(self, config_path: str):
        """Load user-defined campaign from YAML."""
        from benchmarks.scenarios.campaign_loader import load_campaign
        data = load_campaign(config_path)
        cli_logger.info("\n  [CAMPAIGN] Loaded custom campaign: %s", config_path)
        cli_logger.info("  [CAMPAIGN] Name: %s", data["campaign_brief"].get("campaign_name", "N/A"))
        cli_logger.info("  [CAMPAIGN] Products: %d", len(data.get("product_catalog", [])))
        cli_logger.info("  [CAMPAIGN] Channels: %s", ", ".join(data["campaign_brief"].get("channels", [])))

        self._campaign_brief = data["campaign_brief"]
        self._content_task = data["content_generation_task"]
        self._pii_texts = data["pii_test_texts"]
        self._budget_request = data["budget_reallocation_request"]
        self._approval_rules = data["approval_rules"]
        self._simulated_approvals = data["simulated_approvals"]
        self._conversation_history = data["conversation_history"]
        self._expected_recall = data["expected_recall"]
        self._deployment_task = data["deployment_task"]
        self._multimodal_task = data["multimodal_task"]

    async def run_single_framework(
        self,
        framework_id: str,
        scenarios: Optional[List[str]] = None,
    ) -> Dict[str, ScenarioResult]:
        """Run all (or selected) scenarios on a single framework."""
        cli_logger.info("\n%s", "=" * 60)
        cli_logger.info("  BENCHMARKING: %s", framework_id)
        cli_logger.info("%s", "=" * 60)

        adapter = _load_adapter(framework_id)
        if not adapter:
            return {}

        # ── Dry-run mode: validate adapter can load, then skip execution ──
        if self.dry_run:
            cli_logger.info("  [DRY-RUN] Adapter '%s' loaded successfully ✓", framework_id)
            cli_logger.info("  [DRY-RUN] Would run scenarios: %s", scenarios or "all")
            return {}

        # Setup
        try:
            await adapter.setup(self.llm_config)
        except Exception as e:
            logger.error("Setup failed for '%s': %s", framework_id, e, exc_info=True)
            cli_logger.info("  [X] Setup failed: %s", e)
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
                logger.warning("Unknown scenario requested: %s", scenario_id)
                cli_logger.info("  [?] Unknown scenario: %s", scenario_id)
                continue

            cli_logger.info("\n  --- Scenario: %s ---", scenario_id)
            adapter.reset_metrics()

            start = time.time()
            try:
                # Run with timeout protection
                result = await asyncio.wait_for(
                    runner_fn(adapter),
                    timeout=self.timeout_seconds,
                )
                result.total_duration_ms = (time.time() - start) * 1000
                result.started_at = datetime.now().isoformat()
                result.finished_at = datetime.now().isoformat()
                results[scenario_id] = result
                cli_logger.info(
                    "  [+] %s: %s (%dms)",
                    scenario_id, result.status, result.total_duration_ms,
                )
            except asyncio.TimeoutError:
                duration = (time.time() - start) * 1000
                result = ScenarioResult(
                    scenario_id=scenario_id,
                    framework_name=framework_id,
                    status="timeout",
                    error=f"Scenario exceeded {self.timeout_seconds}s timeout",
                    total_duration_ms=duration,
                )
                results[scenario_id] = result
                logger.warning(
                    "Scenario '%s' timed out for '%s' after %.0fms",
                    scenario_id, framework_id, duration,
                )
                cli_logger.info(
                    "  [⏰] %s: TIMEOUT after %ds", scenario_id, self.timeout_seconds,
                )
            except Exception as e:
                duration = (time.time() - start) * 1000
                result = ScenarioResult(
                    scenario_id=scenario_id,
                    framework_name=framework_id,
                    status="failed",
                    error=str(e),
                    total_duration_ms=duration,
                )
                results[scenario_id] = result
                logger.error(
                    "Scenario '%s' failed for '%s': %s",
                    scenario_id, framework_id, e, exc_info=True,
                )
                cli_logger.info("  [X] %s: FAILED — %s", scenario_id, e)

        # Teardown — log errors instead of silently swallowing them
        try:
            await adapter.teardown()
        except Exception as e:
            logger.warning(
                "Teardown failed for '%s': %s (non-fatal)", framework_id, e,
            )

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

        cli_logger.info("\n%s", "#" * 60)
        cli_logger.info(
            "  MIZAN BENCHMARK — %d frameworks x %s scenarios",
            len(framework_ids),
            len(scenarios) if scenarios else "all 7",
        )
        if self.dry_run:
            cli_logger.info("  MODE: DRY-RUN (validation only, no execution)")
        cli_logger.info("%s", "#" * 60)

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

        if self.dry_run:
            cli_logger.info("\n  ✅ DRY-RUN COMPLETE — all adapters validated.")

        return {}

    # ═══════════════════════════════════════════════════════════════
    # Individual scenario runners
    # ═══════════════════════════════════════════════════════════════

    async def _run_orchestration(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 1: Campaign Planning — tests orchestration."""
        agent_specs = _build_agent_specs()
        return await adapter.run_orchestration(
            agent_specs=agent_specs,
            task=self._campaign_brief,
            orchestration_mode="hierarchical",
        )

    async def _run_tool_use(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 2: Content Generation — tests tool use / RAG."""
        agent_specs = [
            AgentSpec(
                name="ContentArchitect",
                role="Content Generator",
                goal=self._content_task["goal"],
                backstory=AGENT_SPECS[1]["backstory"],
            ),
        ]

        # Create a mock RAG tool
        content_task = self._content_task
        def search_catalog(query: str) -> str:
            """Search the product catalog."""
            product = content_task.get("product", {})
            if query.lower() in product.get("name_en", "").lower() or query in product.get("name_ar", ""):
                return json.dumps(product, ensure_ascii=False)
            return "No products found"

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
            task=self._content_task,
            tools=tools,
        )

    async def _run_safety(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 3: PII Scan — tests safety & privacy."""
        return await adapter.run_safety_check(
            text_with_pii=self._pii_texts.get("saudi_text", "") + "\n\n" + self._pii_texts.get("egyptian_text", ""),
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
            task=self._budget_request,
            approval_rules=self._approval_rules,
            simulated_approvals=self._simulated_approvals,
        )

    async def _run_memory(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 5: Cross-Session Chat — tests memory."""
        follow_up = ""
        if self._conversation_history and len(self._conversation_history) > 1:
            follow_up = self._conversation_history[-1].get("messages", [{}])[0].get("content", "")
        elif self._conversation_history:
            follow_up = self._conversation_history[0].get("messages", [{}])[-1].get("content", "")
        return await adapter.run_with_memory(
            conversation_history=self._conversation_history,
            follow_up_query=follow_up,
            expected_recall=self._expected_recall,
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
            task=self._deployment_task,
            inject_failure=inject_failure,
        )

    async def _run_multimodal(self, adapter: BaseFrameworkAdapter) -> ScenarioResult:
        """Scenario 7: Product Image → Ad Copy — tests multimodal."""
        return await adapter.run_multimodal(
            image_path=None,  # Will use product URL from task
            document_path=None,
            task=self._multimodal_task,
        )

    # ═══════════════════════════════════════════════════════════════
    # Output
    # ═══════════════════════════════════════════════════════════════

    def _save_results(self, comparison: Dict):
        """Save results to JSON + HTML report."""
        RESULTS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON (always saved)
        if self.output_format in ("json", "all"):
            json_path = RESULTS_DIR / f"benchmark_{timestamp}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)
            cli_logger.info("\n  [JSON] Saved:   %s", json_path)

        # HTML Report
        if self.output_format in ("html", "all"):
            try:
                html_path = generate_report(
                    comparison,
                    output_dir=str(RESULTS_DIR),
                    filename_prefix=timestamp,
                )
                cli_logger.info("  [HTML] Report:  %s", html_path)
            except Exception as e:
                logger.warning("HTML report generation failed: %s", e, exc_info=True)

        # Markdown summary
        if self.output_format in ("markdown", "all"):
            md_path = RESULTS_DIR / f"benchmark_{timestamp}.md"
            self._save_markdown(comparison, md_path)
            cli_logger.info("  [MD]   Summary: %s", md_path)

    def _save_markdown(self, comparison: Dict, path: Path):
        """Save results as a Markdown table."""
        lines = [
            "# ⚖️ Mizan Benchmark Results",
            f"\n**Date:** {comparison.get('evaluated_at', 'N/A')}",
            f"**Frameworks tested:** {comparison.get('frameworks_count', 0)}",
            "",
            "| Rank | Framework | Score | Orch | Tools | Safety | HITL | Memory | Obs | Multi |",
            "|------|-----------|-------|------|-------|--------|------|--------|-----|-------|",
        ]
        for entry in comparison.get("ranking", []):
            d = entry["dimensions"]
            lines.append(
                f"| {entry['rank']} | {entry['framework']} | {entry['total_score']:.2f} | "
                f"{d.get('orchestration', 0):.1f} | {d.get('tool_use', 0):.1f} | "
                f"{d.get('safety', 0):.1f} | {d.get('human_in_the_loop', 0):.1f} | "
                f"{d.get('memory', 0):.1f} | {d.get('observability', 0):.1f} | "
                f"{d.get('multimodal', 0):.1f} |"
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _print_leaderboard(self, comparison: Dict):
        """Print a formatted leaderboard to console."""
        cli_logger.info("\n%s", "=" * 80)
        cli_logger.info("  MIZAN BENCHMARK LEADERBOARD")
        cli_logger.info("%s", "=" * 80)
        cli_logger.info(
            "  %-5s %-20s %-8s %-6s %-6s %-7s %-6s %-6s %-6s %-6s",
            "Rank", "Framework", "Score", "Orch", "Tools", "Safety", "HITL", "Mem", "Obs", "Multi",
        )
        cli_logger.info("  %s", "-" * 74)

        medals = {1: "#1", 2: "#2", 3: "#3"}
        for entry in comparison["ranking"]:
            dims = entry["dimensions"]
            medal = medals.get(entry["rank"], f"  {entry['rank']}")
            cli_logger.info(
                "  %-5s %-20s %-8.2f %-6.1f %-6.1f %-7.1f %-6.1f %-6.1f %-6.1f %-6.1f",
                medal, entry["framework"], entry["total_score"],
                dims.get("orchestration", 0), dims.get("tool_use", 0),
                dims.get("safety", 0), dims.get("human_in_the_loop", 0),
                dims.get("memory", 0), dims.get("observability", 0),
                dims.get("multimodal", 0),
            )

        cli_logger.info("\n  [*] Best per dimension:")
        for dim, info in comparison.get("best_per_dimension", {}).items():
            cli_logger.info("    %-25s %-20s (%s/10)", dim, info["framework"], info["score"])


# ═══════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════

async def main():
    import argparse
    import os
    from dotenv import load_dotenv

    # Load .env file
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="⚖️ Mizan Benchmark Runner — Evaluate AI agentic frameworks on MENA e-commerce scenarios.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m benchmarks.runner --frameworks crewai langgraph   # Test 2 frameworks
  python -m benchmarks.runner --mock                          # Run with mock LLM (free)
  python -m benchmarks.runner --dry-run                       # Validate all adapters
  python -m benchmarks.runner --timeout 60                    # 60s timeout per scenario
  python -m benchmarks.runner --output-format markdown        # Save as markdown table
        """,
    )
    parser.add_argument("--frameworks", nargs="+", default=None,
                        help="Framework IDs to benchmark (default: all available)")
    parser.add_argument("--scenarios", nargs="+", default=None,
                        help="Scenario IDs to run (default: all 7)")
    parser.add_argument("--llm-provider", default=os.getenv("MODEL_PROVIDER", "groq"), help="LLM provider (groq/openai/google/anthropic/mock)")
    parser.add_argument("--llm-model", default=os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"), help="LLM model name")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock LLM responses (no API keys needed, deterministic)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate adapter loading without running any scenarios")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="Per-scenario timeout in seconds (default: 120)")
    parser.add_argument("--output-format", choices=["json", "html", "markdown", "all"],
                        default="all", help="Output format (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose debug logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-essential output")
    parser.add_argument("--campaign", type=str, default=None,
                        help="Path to custom campaign YAML file (your own content, products, channels)")
    parser.add_argument("--mode", choices=["clean", "full"], default="full",
                        help="Benchmark execution mode (default: full)")
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose, quiet=args.quiet)

    # If --mock, force the mock provider
    provider = "mock" if args.mock else args.llm_provider

    # Dynamically select the API key based on the provider
    api_key = ""
    if provider.lower() == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
    elif provider.lower() == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
    elif provider.lower() in ["google", "gemini"]:
        api_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    elif provider.lower() == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
    elif provider.lower() == "ollama":
        api_key = "ollama"  # Ollama doesn't need an API key
        if args.llm_model == "llama-3.3-70b-versatile":
            args.llm_model = "llama3.2"
    elif provider.lower() == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        # LiteLLM needs the model prefixed with openrouter/
        if not args.llm_model.startswith("openrouter/"):
            args.llm_model = f"openrouter/{args.llm_model}"


    llm_config = {
        "provider": provider,
        "model": args.llm_model,
        "api_key": api_key,
        "mode": args.mode,
    }

    runner = BenchmarkRunner(
        llm_config=llm_config,
        timeout_seconds=args.timeout,
        dry_run=args.dry_run,
        output_format=args.output_format,
        campaign_config=args.campaign,
    )
    await runner.run_all_frameworks(
        framework_ids=args.frameworks,
        scenarios=args.scenarios,
    )


def main_sync():
    """Synchronous entry point for CLI (used by pyproject.toml scripts)."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
