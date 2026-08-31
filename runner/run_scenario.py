"""
run_scenario.py — Run a single scenario against a single framework.

Usage:
    python runner/run_scenario.py --framework crewai --scenario s01_task_decomposition
    python runner/run_scenario.py --framework crewai --scenario s07_pii_redaction_ar --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from frameworks.registry import get_adapter
from scenarios.loader import load_scenario
from shared.llm_config import get_config
from shared.scoring.scorer import BenchmarkScorer
from shared.testing.seeds import set_all_seeds


async def run_scenario(
    framework_id: str,
    scenario_id: str,
    verbose: bool = False,
) -> dict:
    """Run one scenario against one framework and return results."""

    config = get_config()
    set_all_seeds(config.llm.seed)

    print(f"\n{'='*60}")
    print(f"  Framework : {framework_id}")
    print(f"  Scenario  : {scenario_id}")
    print(f"  Model     : {config.llm.model}")
    print(f"  Seed      : {config.llm.seed}")
    print(f"{'='*60}\n")

    # Load scenario
    scenario = load_scenario(scenario_id)

    # Load adapter
    adapter = get_adapter(framework_id)
    await adapter.setup(config.llm.to_dict())

    # Run the appropriate method
    start = time.time()
    result = await _dispatch(adapter, scenario)
    elapsed = time.time() - start

    await adapter.teardown()

    # Score result
    scorer = BenchmarkScorer()

    # Print result
    status_icon = "✅" if result.status == "completed" else "❌"
    print(f"\n{status_icon} Status        : {result.status}")
    print(f"⏱  Duration      : {result.total_duration_ms:.0f}ms")
    print(f"🤖 Agent count   : {result.agent_count}")
    print(f"🔧 Tool calls    : {result.tool_calls}")
    print(f"🔍 Trace entries : {len(result.trace)}")

    if result.error:
        print(f"❌ Error         : {result.error}")

    if verbose and result.output:
        print(f"\n📄 Output:\n{json.dumps(result.output, ensure_ascii=False, indent=2)[:2000]}")

    if verbose and result.trace:
        print(f"\n📊 Trace ({len(result.trace)} entries):")
        for entry in result.trace[:10]:
            print(f"   [{entry.agent_name}] {entry.action}: {entry.output_summary[:80]}")

    # Save result
    output_dir = Path("results/runs") / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{framework_id}_{scenario_id}_{int(time.time())}.json"

    result_dict = {
        "framework": framework_id,
        "scenario": scenario_id,
        "status": result.status,
        "duration_ms": result.total_duration_ms,
        "agent_count": result.agent_count,
        "tool_calls": result.tool_calls,
        "trace_entries": len(result.trace),
        "flags": {
            "used_parallel": result.used_parallel,
            "used_retry": result.used_retry,
            "used_memory": result.used_memory,
            "used_approval_gate": result.used_approval_gate,
            "pii_detected": result.pii_detected,
            "pii_redacted": result.pii_redacted,
        },
        "error": result.error,
        "run_at": datetime.now().isoformat(),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved → {output_path}")
    return result_dict


async def _dispatch(adapter, scenario):
    """Route scenario to the correct adapter method."""
    from shared.contracts.adapter import ScenarioType

    ctx = scenario.context
    agents = scenario.agent_specs
    scenario_type = scenario.scenario_type

    if scenario_type == ScenarioType.ORCHESTRATION:
        return await adapter.run_orchestration(
            agent_specs=agents,
            task=ctx,
            orchestration_mode=ctx.get("orchestration_mode", "sequential"),
        )
    elif scenario_type == ScenarioType.TOOL_USE:
        return await adapter.run_with_tools(
            agent_specs=agents,
            task=ctx,
            tools=[],
        )
    elif scenario_type == ScenarioType.SAFETY:
        texts = ctx.get("texts", {})
        # Run on the most complex text (mixed)
        text = texts.get("mixed_text") or texts.get("saudi_text", str(ctx))
        return await adapter.run_safety_check(
            text_with_pii=text,
            pii_types=list(ctx.get("expected_behavior", {}).get("must_detect", {}).get("mixed_text", {}).keys()),
            jurisdiction=ctx.get("jurisdiction", "KSA"),
        )
    elif scenario_type == ScenarioType.HUMAN_IN_THE_LOOP:
        return await adapter.run_hitl(
            agent_specs=agents,
            task=ctx,
            approval_rules=ctx.get("approval_rules", {}),
            simulated_approvals=ctx.get("simulated_approval", {}),
        )
    elif scenario_type == ScenarioType.MEMORY:
        return await adapter.run_memory(
            agent_specs=agents,
            conversation_history=ctx,
            follow_up=ctx.get("session_2_trigger", {}),
        )
    elif scenario_type == ScenarioType.OBSERVABILITY:
        return await adapter.run_observability(
            agent_specs=agents,
            task=ctx,
        )
    elif scenario_type == ScenarioType.MULTIMODAL:
        return await adapter.run_multimodal(
            agent_specs=agents,
            task=ctx,
        )
    else:
        raise ValueError(f"Unknown scenario type: {scenario_type}")


def main():
    parser = argparse.ArgumentParser(description="Run a single Mizan benchmark scenario")
    parser.add_argument("--framework", "-f", required=True, help="Framework ID (e.g. crewai)")
    parser.add_argument("--scenario", "-s", required=True, help="Scenario ID (e.g. s01_task_decomposition)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show output and trace")
    args = parser.parse_args()

    asyncio.run(run_scenario(args.framework, args.scenario, args.verbose))


if __name__ == "__main__":
    main()
