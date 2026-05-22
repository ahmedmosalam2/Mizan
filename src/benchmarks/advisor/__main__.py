"""
Mizan Advisor CLI — Command-line interface for framework recommendations.

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

Usage:
    PYTHONPATH=src python -m benchmarks.advisor

    # Interactive mode:
    PYTHONPATH=src python -m benchmarks.advisor --interactive

    # Direct query:
    PYTHONPATH=src python -m benchmarks.advisor --use-case customer_service --need hitl memory --scale high

    # List all use cases:
    PYTHONPATH=src python -m benchmarks.advisor --list-use-cases

    # List all frameworks:
    PYTHONPATH=src python -m benchmarks.advisor --list-frameworks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src is on path
SRC = Path(__file__).resolve().parent.parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from benchmarks.advisor.decision_engine import MizanAdvisor


# ── Terminal colors ─────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RED    = "\033[91m"
    PURPLE = "\033[95m"
    BLUE   = "\033[94m"
    WHITE  = "\033[97m"


def bar(pct: float, width: int = 30) -> str:
    filled = int(pct / 100 * width)
    color = C.GREEN if pct >= 70 else C.YELLOW if pct >= 40 else C.RED
    return color + "█" * filled + C.DIM + "░" * (width - filled) + C.RESET


def header() -> None:
    print(f"""
{C.BOLD}{C.PURPLE}
  [MIZAN] AI Framework Advisor
  ====================================================
  Based on real benchmarks across 20 AI agentic frameworks
{C.RESET}""")


def print_recommendation(result, verbose: bool = False) -> None:
    top = result.top_pick
    print(f"\n{C.BOLD}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  Use Case: {C.CYAN}{result.use_case_name}{C.RESET}")
    print(f"{C.BOLD}{'='*60}{C.RESET}\n")

    # Top pick
    print(f"  [#1] Best Pick / الاختيار الأمثل{C.RESET}")
    print(f"     {C.BOLD}{C.GREEN}{top.name}{C.RESET}  {bar(top.score)}  {C.BOLD}{top.score:.0f}%{C.RESET}")
    if top.benchmark_score is not None:
        print(f"     Benchmark Score: {C.CYAN}{top.benchmark_score:.2f}/10{C.RESET}")

    if top.reasons_for:
        print(f"\n  {C.DIM}Why:{C.RESET}")
        for r in top.reasons_for[:4]:
            print(f"     {C.GREEN}+{C.RESET} {r}")

    if top.reasons_against:
        print(f"\n  {C.DIM}Watch out:{C.RESET}")
        for r in top.reasons_against[:2]:
            print(f"     {C.YELLOW}~{C.RESET} {r}")

    # Alternatives
    if result.alternatives:
        print(f"\n{C.BOLD}  Alternatives:{C.RESET}")
        medals = ["[#2]", "[#3]", "   "]
        for i, alt in enumerate(result.alternatives):
            print(f"     {medals[i]} {C.BOLD}{alt.name}{C.RESET}  {bar(alt.score)}  {alt.score:.0f}%")

    # Avoid
    if result.avoid:
        print(f"\n  {C.RED}[X] Avoid for this use case:{C.RESET} {', '.join(result.avoid)}")

    # Requirements
    if result.requirements_matched:
        print(f"\n  {C.GREEN}[OK] Requirements met:{C.RESET} {', '.join(result.requirements_matched)}")
    if result.requirements_unmet:
        print(f"  {C.YELLOW}[!] Not met:{C.RESET} {', '.join(result.requirements_unmet)}")

    # Reasoning
    print(f"\n{C.BOLD}  [*] التوصية / Recommendation:{C.RESET}")
    for line in result.reasoning.split("\n"):
        if line.strip():
            print(f"     {line}")

    # Live Run Output Preview
    if hasattr(result, "live_output_preview") and result.live_output_preview:
        p = result.live_output_preview
        print(f"\n{C.BOLD}  🔍 المعاينة العملية للتشغيل / Live Run Preview (from {p['framework']}):{C.RESET}")
        print(f"     {C.DIM}Scenario: {p['scenario']} | Duration: {p['duration']:.1f}s | Tokens: {p['tokens']}{C.RESET}")
        print(f"     {C.CYAN}────────────────────────────────────────────────────────{C.RESET}")
        for line in p["snippet"].split("\n"):
            print(f"     {C.GREEN}|{C.RESET} {line}")
        print(f"     {C.CYAN}────────────────────────────────────────────────────────{C.RESET}")

    print(f"\n{'='*60}\n")


def interactive_mode(advisor: MizanAdvisor) -> None:
    header()
    print(f"{C.BOLD}  وضع الاستشارة التفاعلي / Interactive Advisory Mode{C.RESET}\n")

    # Step 1: Use case
    print(f"{C.CYAN}Step 1: اختار الـ Use Case الأقرب لمشروعك:{C.RESET}\n")
    cases = advisor.list_use_cases()
    for i, uc in enumerate(cases, 1):
        print(f"  {C.BOLD}{i}.{C.RESET} {uc['name']} — {C.DIM}{uc['arabic']}{C.RESET}")
    print(f"  {C.BOLD}{len(cases)+1}.{C.RESET} Custom / مخصص\n")

    try:
        choice = int(input(f"  {C.YELLOW}اختيارك (رقم):{C.RESET} ").strip()) - 1
        use_case = cases[choice]["id"] if 0 <= choice < len(cases) else None
    except (ValueError, IndexError):
        use_case = None

    # Step 2: Extra requirements
    print(f"\n{C.CYAN}Step 2: إيه الـ Features الضرورية لمشروعك؟{C.RESET}")
    print(f"  {C.DIM}(اكتب مفصولة بفاصلة، أو Enter للتخطي){C.RESET}")
    print(f"  Options: hitl, memory, multimodal, streaming, pii, low_code, type_safety\n")
    reqs_raw = input(f"  {C.YELLOW}Features:{C.RESET} ").strip()
    requirements = [r.strip() for r in reqs_raw.split(",") if r.strip()] if reqs_raw else []

    # Step 3: Scalability
    print(f"\n{C.CYAN}Step 3: هتضيف على المشروع features بعدين؟ (Scalability){C.RESET}")
    print("  1. No — MVP فقط، مش هعدّل عليه كتير")
    print("  2. Maybe — هضيف حاجات بس مش كتير")
    print("  3. Yes — هيكبر كتير وهضيف features كتير بعدين\n")
    scale_map = {"1": "low", "2": "medium", "3": "high"}
    scale_input = input(f"  {C.YELLOW}اختيارك (1/2/3):{C.RESET} ").strip()
    scalability = scale_map.get(scale_input, "medium")

    # Step 4: Team experience
    print(f"\n{C.CYAN}Step 4: خبرة الـ Team بـ AI Frameworks؟{C.RESET}")
    print("  1. Beginner — بداية مع الـ AI Frameworks")
    print("  2. Medium — عندنا شوية خبرة")
    print("  3. Expert — خبرة كاملة\n")
    exp_map = {"1": "beginner", "2": "medium", "3": "expert"}
    exp_input = input(f"  {C.YELLOW}اختيارك (1/2/3):{C.RESET} ").strip()
    experience = exp_map.get(exp_input, "medium")

    # Step 5: Collaboration Patterns
    print(f"\n{C.CYAN}Step 5: محتاج الـ Agents يتعاونوا مع بعض بأي شكل؟ (Collaboration Pattern){C.RESET}")
    print("  1. No Preference / أي نمط")
    print("  2. Hierarchical — رئيس مرؤوس (إيجنت مدير يوزع المهام على موظفين)")
    print("  3. Graph — شبكة معقدة (انتقالات مخصصة، شروط، تكرار دوري)")
    print("  4. Delegation — تفويض ديناميكي (إيجنت يستدعي إيجنت كأداة)")
    print("  5. Single Agent — إيجنت منفرد فقط")
    collab_map = {"1": "any", "2": "hierarchical", "3": "graph", "4": "delegation", "5": "single_agent"}
    collab_input = input(f"  {C.YELLOW}اختيارك (1/2/3/4/5):{C.RESET} ").strip()
    collaboration = collab_map.get(collab_input, "any")

    # Step 6: Production
    print(f"\n{C.CYAN}Step 6: هل ده للـ Production؟{C.RESET}")
    prod_input = input(f"  {C.YELLOW}(y/n):{C.RESET} ").strip().lower()
    production = prod_input != "n"

    # Run recommendation
    print(f"\n{C.DIM}  جاري التحليل...{C.RESET}\n")
    result = advisor.recommend(
        use_case=use_case,
        requirements=requirements,
        scalability=scalability,
        team_experience=experience,
        production=production,
        collaboration=collaboration,
    )
    print_recommendation(result, verbose=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mizan-advise",
        description="Mizan AI Framework Advisor — اختار الـ Framework الصح لمشروعك",
    )
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive advisory mode")
    parser.add_argument("--use-case", "-u", help="Use case ID (e.g. customer_service)")
    parser.add_argument("--need", "-n", nargs="+", help="Required features (e.g. hitl memory multimodal)")
    parser.add_argument("--scale", choices=["low", "medium", "high"], default="medium", help="Scalability need")
    parser.add_argument("--complexity", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--experience", choices=["beginner", "medium", "expert"], default="medium")
    parser.add_argument("--collaboration", choices=["any", "hierarchical", "graph", "delegation", "single_agent"], default="any")
    parser.add_argument("--no-production", action="store_true", help="Prototype only")
    parser.add_argument("--list-use-cases", action="store_true")
    parser.add_argument("--list-frameworks", action="store_true")

    args = parser.parse_args()
    advisor = MizanAdvisor()

    if args.list_use_cases:
        header()
        print(f"{C.BOLD}  Available Use Cases:{C.RESET}\n")
        for uc in advisor.list_use_cases():
            print(f"  {C.CYAN}{uc['id']:<25}{C.RESET} {uc['name']} — {C.DIM}{uc['arabic']}{C.RESET}")
        return

    if args.list_frameworks:
        header()
        print(f"{C.BOLD}  Profiled Frameworks ({len(advisor.list_frameworks())} total):{C.RESET}\n")
        for fw in advisor.list_frameworks():
            p = advisor.profiles[fw]
            prod = f"{C.GREEN}Production-Ready{C.RESET}" if p.get("production_ready") else f"{C.YELLOW}Experimental{C.RESET}"
            print(f"  {C.BOLD}{p['name']:<20}{C.RESET} {prod}  {C.DIM}{p['summary'][:60]}...{C.RESET}")
        return

    if args.interactive:
        interactive_mode(advisor)
        return

    # Direct mode
    header()
    result = advisor.recommend(
        use_case=args.use_case,
        requirements=args.need or [],
        scalability=args.scale,
        complexity=args.complexity,
        team_experience=args.experience,
        production=not args.no_production,
        collaboration=args.collaboration,
    )
    print_recommendation(result, verbose=True)


if __name__ == "__main__":
    main()
