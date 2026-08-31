"""
Scenario Loader for Mizan Benchmark.

Loads all YAML fixtures, initializes SQLite database and seed data,
and returns a fully prepared RamadanScenario instance.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from mizan.adapters.base import ALL_PROBES, ProbeId, RamadanScenario
from mizan.services.database import DatabaseService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_yaml(file_name: str) -> Any:
    """Load a fixture yaml file."""
    path = FIXTURES_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_scenario(
    probes: Optional[List[ProbeId]] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    db_path: str = "mizan_ramadan.db",
) -> RamadanScenario:
    """
    Build and initialize the complete RamadanScenario environment.
    """
    campaign_brief = load_yaml("campaign_brief.yaml")
    products = load_yaml("products.yaml")
    customers = load_yaml("customers.yaml")
    channels = load_yaml("channels.yaml")
    session_history = load_yaml("session_history.yaml")
    pii_texts = load_yaml("pii_texts.yaml")
    ground_truth = load_yaml("ground_truth.yaml")

    # Initialize and seed real database
    db_service = DatabaseService(db_path=db_path)
    db_service.seed_products(products)
    db_service.seed_customers(customers)

    # Resolve LLM Config
    resolved_llm_config = llm_config or {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": os.environ.get("OPENAI_BASE_URL", None),
        "temperature": 0.2,
        "seed": int(os.environ.get("MIZAN_SEED", "42")),
    }

    return RamadanScenario(
        campaign_brief=campaign_brief,
        products=products,
        customers=customers,
        channels=channels,
        session_history=session_history,
        pii_texts=pii_texts,
        ground_truth=ground_truth,
        llm_config=resolved_llm_config,
        db_path=db_path,
        probes_to_run=probes or list(ALL_PROBES),
    )
