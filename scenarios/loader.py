"""
Scenario Loader — Reads scenario configs and fixtures, returns ScenarioInput.

Usage:
    from scenarios.loader import load_scenario, list_scenarios
    scenario = load_scenario("s01_task_decomposition")
"""

from pathlib import Path
from typing import Dict, List, Optional
import json
import yaml

from shared.contracts.adapter import AgentSpec, ScenarioInput, ScenarioType

SCENARIOS_ROOT = Path(__file__).parent

AGENT_SPECS: List[AgentSpec] = [
    AgentSpec(name="CampaignCommander", role="Campaign Manager & Orchestrator",
             goal="Decompose Ramadan campaign briefs into sub-tasks and coordinate execution across Saudi and Egyptian markets.",
             backstory="Senior marketing strategist with 10 years MENA e-commerce experience.", can_delegate=True, memory=False),
    AgentSpec(name="ContentArchitect", role="Bilingual Content Generator",
             goal="Generate high-quality bilingual (Arabic/English) campaign content.",
             backstory="Expert Arabic copywriter fluent in Gulf and Egyptian Arabic.", memory=False),
    AgentSpec(name="ChannelDeployer", role="Multi-Channel Campaign Deployer",
             goal="Deploy campaigns across Meta, Google, Snapchat, TikTok, WhatsApp, SMS, and email.",
             backstory="Digital advertising operations specialist for MENA platforms.", memory=False),
    AgentSpec(name="AnalyticsEngine", role="Campaign Performance Analyst",
             goal="Monitor performance, compute ROAS/CPA/CTR, recommend budget reallocations.",
             backstory="Data analyst specialised in MENA e-commerce marketing analytics.", memory=False),
    AgentSpec(name="CustomerEngagement", role="Customer Service Agent",
             goal="Handle customer inquiries via WhatsApp. Answer questions, process orders, escalate issues.",
             backstory="Customer service rep for MENA e-commerce. Speaks Gulf and Egyptian Arabic.", memory=False),
    AgentSpec(name="ComplianceGuardian", role="Privacy & Compliance Officer",
             goal="Scan content for PII violations. Detect/redact Saudi/Egyptian national IDs, phones, personal data.",
             backstory="Data protection officer for Saudi PDPL and Egypt Law 151/2020.", memory=False),
]


def load_scenario(scenario_id: str) -> ScenarioInput:
    """Load a scenario by ID from its config.yaml."""
    scenario_dir = _find_scenario_dir(scenario_id)
    if not scenario_dir:
        raise FileNotFoundError(f"Scenario '{scenario_id}' not found")

    config_path = scenario_dir / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found in {scenario_dir}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Load fixtures
    fixtures = {}
    fixtures_dir = scenario_dir / "fixtures"
    if fixtures_dir.exists():
        for fp in fixtures_dir.glob("*.yaml"):
            with open(fp, encoding="utf-8") as f:
                fixtures[fp.stem] = yaml.safe_load(f)
        for fp in fixtures_dir.glob("*.json"):
            with open(fp, encoding="utf-8") as f:
                fixtures[fp.stem] = json.load(f)

    # Load ground truth
    ground_truth = {}
    gt_path = scenario_dir / "ground_truth.yaml"
    if gt_path.exists():
        with open(gt_path, encoding="utf-8") as f:
            ground_truth = yaml.safe_load(f) or {}

    needed = config.get("agents", [a.name for a in AGENT_SPECS])
    agents = [a for a in AGENT_SPECS if a.name in needed]

    return ScenarioInput(
        scenario_id=scenario_id,
        scenario_type=ScenarioType(config.get("type", "orchestration")),
        description=config.get("description", ""),
        task_goal=config.get("task_goal", ""),
        context={**config.get("context", {}), **fixtures, "ground_truth": ground_truth},
        agent_specs=agents,
        expected_behavior=config.get("expected_behavior", {}),
        timeout_seconds=config.get("timeout_seconds", 120.0),
    )


def list_scenarios(category: Optional[str] = None) -> List[str]:
    """List all available scenario IDs."""
    ids = []
    for subdir in sorted(SCENARIOS_ROOT.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_") or subdir.name.startswith("."):
            continue
        for scenario_dir in sorted(subdir.iterdir()):
            if scenario_dir.is_dir() and (scenario_dir / "config.yaml").exists():
                if category is None or subdir.name == category:
                    ids.append(scenario_dir.name)
    return ids


def _find_scenario_dir(scenario_id: str) -> Optional[Path]:
    for subdir in SCENARIOS_ROOT.iterdir():
        if not subdir.is_dir():
            continue
        candidate = subdir / scenario_id
        if candidate.is_dir():
            return candidate
    return None
