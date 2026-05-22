"""
Campaign Loader — Reads a user-defined campaign YAML file and converts it
into the benchmark test_data format so the runner can use custom campaigns.

Usage:
    from benchmarks.scenarios.campaign_loader import load_campaign
    data = load_campaign("campaign_config.yaml")
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_campaign(config_path: str) -> Dict[str, Any]:
    """
    Load a user-defined campaign YAML and convert to benchmark-ready format.

    Returns a dict with all the keys the runner expects:
    - campaign_brief, product_catalog, content_generation_task,
    - pii_test_texts, budget_reallocation_request, conversation_history,
    - deployment_task, multimodal_task, etc.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Campaign config not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    campaign = config.get("campaign", {})
    products = config.get("products", [])
    channels = config.get("channels", [])
    conversations = config.get("customer_conversations", {})
    pii_data = config.get("pii_test_data", {})
    budget_rules = config.get("budget_rules", {})

    # ── 1. Campaign Brief (Orchestration) ─────────────────────
    markets_dict = {}
    target_audiences = {}
    for m in campaign.get("markets", []):
        country = m["country"]
        markets_dict[country] = {"amount": m["budget"], "currency": m["currency"]}
        target_audiences[country] = m.get("target_audience", "")

    campaign_brief = {
        "campaign_name": campaign.get("name", "Custom Campaign"),
        "company": campaign.get("company", "Unknown"),
        "markets": list(markets_dict.keys()),
        "budget": markets_dict,
        "channels": [ch["name"] for ch in channels if ch.get("enabled", True)],
        "target_audiences": target_audiences,
        "objectives": campaign.get("objectives", []),
        "content_requirements": {
            "ad_variants": len(products) * 3,
            "languages": ["ar", "en"],
            "formats": [ch.get("ad_type", "message") for ch in channels],
        },
        "start_date": campaign.get("start_date", ""),
        "end_date": campaign.get("end_date", ""),
        "special_notes": campaign.get("special_notes", ""),
    }

    # ── 2. Product Catalog + Content Generation Task ──────────
    product_catalog = []
    for p in products:
        product_catalog.append({
            "name_en": p.get("name_en", ""),
            "name_ar": p.get("name_ar", ""),
            "price_sar": p.get("price_sar", 0),
            "price_egp": p.get("price_egp", 0),
            "category": p.get("category", ""),
            "description_en": p.get("description", ""),
            "description_ar": p.get("description", ""),
            "image_url": p.get("image_url", ""),
        })

    content_generation_task = {
        "goal": f"Generate marketing content for {campaign.get('name', 'campaign')}",
        "product": product_catalog[0] if product_catalog else {},
        "channels": [ch["name"] for ch in channels if ch.get("enabled", True)],
        "languages": ["ar", "en"],
    }

    # ── 3. PII Test Data ──────────────────────────────────────
    pii_texts = pii_data.get("texts", [])
    pii_test_texts = {
        "saudi_text": pii_texts[0] if len(pii_texts) > 0 else "",
        "egyptian_text": pii_texts[1] if len(pii_texts) > 1 else "",
    }
    expected_pii = pii_data.get("expected_detections", [])

    # ── 4. Budget Reallocation Request ────────────────────────
    budget_reallocation = {
        "goal": f"Optimize budget allocation for {campaign.get('name', 'campaign')}",
        "total_budget": sum(m["budget"] for m in campaign.get("markets", [])),
        "channels": {ch["name"]: {"current_spend_pct": round(100 / max(len(channels), 1))}
                     for ch in channels if ch.get("enabled", True)},
        "approval_threshold": budget_rules.get("approval_required_above", 10000),
        "max_single_channel_pct": budget_rules.get("max_single_channel_percent", 40),
    }
    simulated_approvals = budget_rules.get("simulated_approvals", [])
    approval_rules = {
        "threshold": budget_rules.get("approval_required_above", 10000),
        "max_single_channel": budget_rules.get("max_single_channel_percent", 40),
    }

    # ── 5. Conversation History (Memory) ──────────────────────
    conversation_history = []
    if isinstance(conversations, dict):
        conversation_history = conversations.get("sessions", [])
    elif isinstance(conversations, list):
        conversation_history = [c for c in conversations if isinstance(c, dict) and "messages" in c]

    follow_up = []
    if isinstance(conversations, dict):
        follow_up = conversations.get("follow_up_expected", [])

    expected_recall = follow_up

    # ── 6. Deployment Task ────────────────────────────────────
    deploy_channels = []
    for ch in channels:
        if ch.get("enabled", True):
            deploy_channels.append({
                "name": ch["name"],
                "should_succeed": not ch.get("should_fail", False),
                "error": ch.get("error_type", ""),
                "message_template": ch.get("message_template", ch.get("body_template", "")),
            })

    deployment_task = {
        "goal": f"Deploy {campaign.get('name', 'campaign')} across all channels",
        "channels": deploy_channels,
    }

    # ── 7. Multimodal Task ────────────────────────────────────
    multimodal_task = {
        "goal": f"Generate visual ad content for {product_catalog[0]['name_ar'] if product_catalog else 'product'}",
        "product": product_catalog[0] if product_catalog else {},
        "output_format": "carousel",
        "language": "ar_gulf",
    }

    return {
        "campaign_brief": campaign_brief,
        "product_catalog": product_catalog,
        "content_generation_task": content_generation_task,
        "pii_test_texts": pii_test_texts,
        "expected_pii_detections": expected_pii,
        "budget_reallocation_request": budget_reallocation,
        "simulated_approvals": simulated_approvals,
        "approval_rules": approval_rules,
        "conversation_history": conversation_history,
        "expected_recall": expected_recall,
        "expected_recall": expected_recall,
        "deployment_task": deployment_task,
        "multimodal_task": multimodal_task,
    }
