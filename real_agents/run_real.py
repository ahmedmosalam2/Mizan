"""
Run Real Agents — Execute content + PII agents with real LLM calls.

Usage:
    python real_agents/run_real.py
    python real_agents/run_real.py --agent content
    python real_agents/run_real.py --agent pii
    python real_agents/run_real.py --agent all
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from real_agents.llm_client import LLMClient
from real_agents.content_agent import run_content_agent, PRODUCT_CATALOG, ContentResult
from real_agents.pii_agent import run_pii_benchmark, PIIResult


def make_client() -> LLMClient:
    """Create LLM client from env vars or defaults to Ollama."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

    if provider == "ollama":
        model = "ollama/llama3.2"
        api_key = ""
        print(f">> Using Local Ollama (llama3.2)")
    elif gemini_key and provider == "gemini":
        model = "gemini/gemini-2.5-flash"
        api_key = gemini_key
        print(f">> Using Gemini directly (free)")
    elif openrouter_key and provider == "openrouter":
        model = "openrouter/google/gemini-2.5-flash"
        api_key = openrouter_key
        print(f">> Using OpenRouter")
    else:
        # Fallback to Ollama if no keys
        model = "ollama/llama3.2"
        api_key = ""
        print(f">> Using Local Ollama (llama3.2)")

    print(f">> Model: {model}")
    return LLMClient(model=model, api_key=api_key)


def run_content_benchmark(client: LLMClient):
    """Run content agent on all products."""
    print("\n" + "=" * 70)
    print("  📝 CONTENT GENERATION AGENT — Real Results")
    print("=" * 70)

    all_results: list[ContentResult] = []

    for product in PRODUCT_CATALOG:
        print(f"\n🔄 Generating ads for: {product['name_en']}...")
        result = run_content_agent(client, product)
        all_results.append(result)
        print(result.summary())

        # Print actual generated content
        if result.parsed_output:
            print(f"\n📄 Generated Content:")
            for variant_key, variant in result.parsed_output.items():
                print(f"\n  [{variant_key}]")
                if isinstance(variant, dict):
                    for k, v in variant.items():
                        if isinstance(v, list):
                            print(f"    {k}: {v}")
                        else:
                            val_str = str(v)
                            print(f"    {k}: {val_str[:100]}")

    # Summary
    print("\n" + "=" * 70)
    print("  📊 CONTENT AGENT — SUMMARY")
    print("=" * 70)

    total_tokens = 0
    total_cost = 0.0
    total_latency = 0.0
    total_checks = 0
    total_passed = 0

    for r in all_results:
        if r.llm_stats:
            total_tokens += r.llm_stats["total_tokens"]
            total_cost += r.llm_stats["total_cost_usd"]
            total_latency += r.llm_stats["total_latency_ms"]
        passed = sum(1 for c in r.quality_checks if c.passed)
        total_checks += len(r.quality_checks)
        total_passed += passed

    print(f"  Products tested : {len(all_results)}")
    print(f"  Quality checks  : {total_passed}/{total_checks} passed ({total_passed/max(total_checks,1)*100:.0f}%)")
    print(f"  Total tokens    : {total_tokens:,}")
    print(f"  Total cost      : ${total_cost:.6f}")
    print(f"  Total latency   : {total_latency:.0f}ms")
    print(f"  Avg per product : {total_latency/max(len(all_results),1):.0f}ms")


def run_pii_test(client: LLMClient):
    """Run PII agent on test corpus."""
    print("\n" + "=" * 70)
    print("  🔒 PII DETECTION AGENT — Regex vs LLM")
    print("=" * 70)

    results = run_pii_benchmark(client)

    for r in results:
        print(r.summary())

    # Summary
    print("\n" + "=" * 70)
    print("  📊 PII AGENT — SUMMARY")
    print("=" * 70)

    total_regex = sum(len(r.regex_matches) for r in results)
    total_llm = sum(len(r.llm_matches) for r in results)
    total_llm_added = sum(len(r.llm_added_value) for r in results)
    total_regex_ms = sum(r.regex_time_ms for r in results)
    total_llm_ms = sum(r.llm_time_ms for r in results)
    total_cost = sum(r.llm_stats.get("total_cost_usd", 0) for r in results if r.llm_stats)
    total_tokens = sum(r.llm_stats.get("total_tokens", 0) for r in results if r.llm_stats)

    print(f"  Texts tested      : {len(results)}")
    print(f"  Regex matches     : {total_regex} (in {total_regex_ms:.1f}ms)")
    print(f"  LLM matches       : {total_llm} (in {total_llm_ms:.0f}ms)")
    print(f"  LLM added value   : {total_llm_added} new findings regex missed")
    print(f"  LLM total tokens  : {total_tokens:,}")
    print(f"  LLM total cost    : ${total_cost:.6f}")
    print(f"  Speed ratio       : LLM is {total_llm_ms/max(total_regex_ms, 0.1):.0f}x slower than regex")
    print(f"\n  💡 Verdict: ", end="")
    if total_llm_added > 0:
        print(f"LLM found {total_llm_added} things regex couldn't! Worth the ${total_cost:.4f}.")
    else:
        print(f"LLM added nothing over regex. Save your ${total_cost:.4f}.")


def save_results(content_results=None, pii_results=None):
    """Save results to file."""
    output_dir = Path("real_agents/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if content_results:
        path = output_dir / f"content_{timestamp}.json"
        data = []
        for r in content_results:
            data.append({
                "product": r.product["sku"],
                "quality_score": r.quality_score,
                "checks_passed": sum(1 for c in r.quality_checks if c.passed),
                "checks_total": len(r.quality_checks),
                "llm_stats": r.llm_stats,
                "output": r.parsed_output,
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Content results saved → {path}")


def main():
    parser = argparse.ArgumentParser(description="Run Mizan Real Agents")
    parser.add_argument("--agent", choices=["content", "pii", "all"], default="all",
                        help="Which agent to run")
    args = parser.parse_args()

    client = make_client()

    if args.agent in ("content", "all"):
        run_content_benchmark(client)

    if args.agent in ("pii", "all"):
        run_pii_test(client)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
