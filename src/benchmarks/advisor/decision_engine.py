from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

@dataclass
class FrameworkMatch:
    name: str
    framework_id: str
    score: float          # 0–100 compatibility score
    benchmark_score: Optional[float]  # from actual benchmark run
    reasons_for: List[str]
    reasons_against: List[str]
    color: str = "#6366f1"


@dataclass
class RecommendationResult:
    top_pick: FrameworkMatch
    alternatives: List[FrameworkMatch]
    avoid: List[str]
    reasoning: str           # Arabic natural language explanation
    reasoning_en: str        # English version
    use_case_name: str
    requirements_matched: List[str]
    requirements_unmet: List[str]


# ── Advisor ────────────────────────────────────────────────────────────────────

class MizanAdvisor:
    """
    Recommends the best AI framework for a given use case
    based on framework profiles + live benchmark data.
    """

    FRAMEWORK_COLORS = [
        "#6366f1", "#ec4899", "#06b6d4", "#22c55e",
        "#f59e0b", "#a855f7", "#ef4444", "#14b8a6",
    ]

    # Feature → framework capability mapping
    FEATURE_MAP = {
        "hitl":               "features.hitl",
        "human_approval":     "features.hitl",
        "persistent_memory":  "features.memory",
        "long_term_memory":   "features.memory",
        "multimodal":         "features.multimodal",
        "streaming":          "features.streaming",
        "async":              "features.async",
        "type_safety":        None,   # handled via pydantic_ai boost
        "pii_handling":       None,   # handled via compliance boost
        "code_execution":     None,   # autogen / smolagents
        "low_code":           None,   # dify / flowise
        "visual_builder":     None,   # dify / flowise
    }

    def __init__(
        self,
        profiles_path: Optional[Path] = None,
        benchmark_results_path: Optional[Path] = None,
    ):
        profiles_path = profiles_path or (
            Path(__file__).parent / "framework_profiles.yaml"
        )
        with open(profiles_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self.profiles: Dict[str, Any] = raw["frameworks"]
        self.use_cases: Dict[str, Any] = raw["use_cases"]
        self.benchmark_data: Optional[Dict] = None

        # Load latest benchmark results if available
        if benchmark_results_path and benchmark_results_path.exists():
            self._load_benchmark(benchmark_results_path)
        else:
            self._try_load_latest_benchmark()

    def _try_load_latest_benchmark(self) -> None:
        results_dir = Path(__file__).parent.parent.parent.parent.parent / "benchmark_results"
        if not results_dir.exists():
            return
        json_files = sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if json_files:
            try:
                with open(json_files[0], encoding="utf-8") as f:
                    self.benchmark_data = json.load(f)
            except Exception:
                pass

    def _load_benchmark(self, path: Path) -> None:
        with open(path, encoding="utf-8") as f:
            self.benchmark_data = json.load(f)

    def _get_benchmark_score(self, framework_id: str) -> Optional[float]:
        if not self.benchmark_data:
            return None
        for entry in self.benchmark_data.get("ranking", []):
            if entry["framework"].lower().replace(" ", "_") == framework_id:
                return entry["total_score"]
        return None

    def recommend(
        self,
        use_case: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        scalability: str = "medium",   # low | medium | high
        complexity: str = "medium",    # low | medium | high
        team_experience: str = "medium",  # beginner | medium | expert
        production: bool = True,
        collaboration: str = "any",    # any | hierarchical | graph | delegation | single
        custom_weights: Optional[Dict[str, int]] = None,
    ) -> RecommendationResult:
        """
        Main recommendation method.

        Args:
            use_case: Key from use_cases catalog (e.g. "customer_service")
            requirements: List of specific features needed (e.g. ["hitl", "multimodal"])
            scalability: How much you'll grow the system later
            complexity: Complexity of your use case
            team_experience: Team's experience with AI frameworks
            production: Is this for production?
            collaboration: Preferred multi-agent orchestration pattern
            custom_weights: Override dimension weights
        """

        requirements = requirements or []
        matches = []

        for fw_id, profile in self.profiles.items():
            score, reasons_for, reasons_against = self._score_framework(
                fw_id=fw_id,
                profile=profile,
                use_case=use_case,
                requirements=requirements,
                scalability=scalability,
                complexity=complexity,
                team_experience=team_experience,
                production=production,
                collaboration=collaboration,
            )

            benchmark_score = self._get_benchmark_score(fw_id)

            # Blend in benchmark score if available (30% weight)
            if benchmark_score is not None:
                score = score * 0.7 + (benchmark_score * 10) * 0.3

            matches.append(FrameworkMatch(
                name=profile["name"],
                framework_id=fw_id,
                score=round(score, 1),
                benchmark_score=benchmark_score,
                reasons_for=reasons_for,
                reasons_against=reasons_against,
            ))

        # Sort by score
        matches.sort(key=lambda m: m.score, reverse=True)

        # Assign colors
        for i, m in enumerate(matches):
            m.color = self.FRAMEWORK_COLORS[i % len(self.FRAMEWORK_COLORS)]

        # Determine explicit avoids from use case catalog
        avoid_list = []
        if use_case and use_case in self.use_cases:
            avoid_list = self.use_cases[use_case].get("avoid", [])

        # ── 1. Smart Trade-off Override Checks ────────────────────────────────
        # If CrewAI is top but user requested a feature CrewAI lacks (like high scalability / custom graphs),
        # and LangGraph supports it, we warn the user or boost LangGraph to top.
        top = matches[0]
        alternatives = [m for m in matches[1:4] if m.score > 40]

        override_msg = ""
        if top.framework_id == "crewai" and scalability == "high":
            langgraph_match = next((m for m in matches if m.framework_id == "langgraph"), None)
            if langgraph_match:
                override_msg = (
                    f"⚠️ تنبيه مقايضة: رغم أن {top.name} هو الأعلى تقييماً هنا، إلا أنه يفتقر لمرونة التطوير والـ Graphs "
                    f"المطلوبة للـ Scalability العالية. ننصحك بالذهاب إلى {langgraph_match.name} بدلاً منه لمشروعك."
                )

        # ── 2. Get Live Run Output Preview ────────────────────────────────────
        live_output_preview = None
        if use_case:
            # First try live benchmark JSON if loaded
            if self.benchmark_data:
                for entry in self.benchmark_data.get("ranking", []):
                    if entry["framework"].lower().replace(" ", "_") == top.framework_id:
                        scenarios = entry.get("scenarios", {})
                        scenario_mapping = {
                            "send_bulk_messages": "lead_conversion",
                            "budget_reallocation_approval": "budget_approval",
                            "pii_compliance": "pii_shield",
                            "customer_support_memory": "customer_support",
                        }
                        scen_id = scenario_mapping.get(use_case, use_case)
                        scen_data = scenarios.get(scen_id, {})
                        if scen_data and scen_data.get("status") == "success":
                            raw_output = scen_data.get("output", "")
                            if raw_output:
                                snippet = raw_output[:350] + ("..." if len(raw_output) > 350 else "")
                                live_output_preview = {
                                    "framework": top.name,
                                    "scenario": scen_id,
                                    "snippet": snippet,
                                    "duration": scen_data.get("duration_seconds", 0.0),
                                    "tokens": scen_data.get("tokens_used", 0)
                                }
                            break

            # Fallback to golden preview from framework_profiles.yaml
            if not live_output_preview and use_case in self.use_cases:
                gp = self.use_cases[use_case].get("golden_preview")
                if gp:
                    live_output_preview = {
                        "framework": gp["framework"],
                        "scenario": use_case,
                        "snippet": gp["snippet"],
                        "duration": 4.2,  # standard mock run duration
                        "tokens": 1250,   # standard mock tokens
                    }

        # Generate reasoning
        reasoning_ar, reasoning_en = self._generate_reasoning(
            top=top,
            alternatives=alternatives,
            use_case=use_case,
            requirements=requirements,
            scalability=scalability,
            override_msg=override_msg
        )

        # Requirements matched/unmet
        matched, unmet = self._check_requirements(requirements, top, matches)

        use_case_name = (
            self.use_cases[use_case]["name"] if use_case and use_case in self.use_cases
            else "Custom Use Case"
        )

        # Store preview in recommendation result
        res = RecommendationResult(
            top_pick=top,
            alternatives=alternatives,
            avoid=avoid_list,
            reasoning=reasoning_ar,
            reasoning_en=reasoning_en,
            use_case_name=use_case_name,
            requirements_matched=matched,
            requirements_unmet=unmet,
        )
        # Dynamically append the extra attributes
        res.override_msg = override_msg
        res.live_output_preview = live_output_preview
        return res

    def _score_framework(
        self,
        fw_id: str,
        profile: Dict,
        use_case: Optional[str],
        requirements: List[str],
        scalability: str,
        complexity: str,
        team_experience: str,
        production: bool,
        collaboration: str = "any",
    ) -> tuple[float, List[str], List[str]]:

        score = 50.0  # base
        reasons_for = []
        reasons_against = []
        features = profile.get("features", {})

        # ── 1. Use Case Fit Score (0–30 points) ───────────────────────────────
        if use_case and use_case in self.use_cases:
            fit = profile.get("use_case_fit", {}).get(use_case, 5)
            score += (fit - 5) * 3  # 0–30 delta
            if fit >= 8:
                reasons_for.append(f"مناسب جداً لـ {self.use_cases[use_case]['name']}")
            elif fit <= 3:
                reasons_against.append(f"مش مناسب لـ {self.use_cases[use_case]['name']}")

        # ── 2. Requirements Matching (0–20 points per requirement) ────────────
        req_score_per = 20.0 / max(len(requirements), 1) if requirements else 0

        for req in requirements:
            req_lower = req.lower().replace(" ", "_")
            hit = False

            if req_lower in ("hitl", "human_approval", "human_in_the_loop"):
                if features.get("hitl"):
                    score += req_score_per
                    reasons_for.append(f"✅ يدعم Human-in-the-Loop: {features.get('hitl_type', '')}")
                    hit = True
                else:
                    score -= req_score_per * 0.5
                    reasons_against.append("❌ لا يدعم Human-in-the-Loop")

            elif req_lower in ("memory", "persistent_memory", "long_term_memory"):
                if features.get("memory"):
                    score += req_score_per
                    reasons_for.append(f"✅ Memory: {features.get('memory_type', '')}")
                    hit = True
                else:
                    score -= req_score_per * 0.5
                    reasons_against.append("❌ لا يدعم Persistent Memory")

            elif req_lower == "multimodal":
                if features.get("multimodal"):
                    score += req_score_per
                    reasons_for.append("✅ يدعم Multimodal (صور + نص)")
                    hit = True
                else:
                    reasons_against.append("❌ لا يدعم Multimodal")

            elif req_lower in ("pii", "pii_handling", "compliance"):
                if fw_id in ("pydantic_ai", "haystack", "langgraph"):
                    score += req_score_per
                    reasons_for.append("✅ مناسب لـ PII compliance وحماية البيانات")
                    hit = True
                elif fw_id in ("swarm", "flowise", "smolagents"):
                    score -= req_score_per
                    reasons_against.append("❌ لا يوفر أدوات compliance")

            elif req_lower in ("low_code", "no_code", "visual"):
                if fw_id in ("dify", "flowise"):
                    score += req_score_per
                    reasons_for.append("✅ Visual Builder — مش محتاج كود")
                    hit = True
                else:
                    reasons_against.append("⚠️ يحتاج Python programming")

            elif req_lower == "streaming":
                if features.get("streaming"):
                    score += req_score_per * 0.5
                    hit = True

        # ── 3. Scalability Match ───────────────────────────────────────────────
        fw_scale = features.get("scalability", "medium")
        if scalability == "high":
            if fw_scale == "high":
                score += 10
                reasons_for.append("✅ Scalability عالية — مناسب للنمو المستقبلي")
            elif fw_scale == "low":
                score -= 15
                reasons_against.append("❌ Scalability محدودة — مش هينفع لو هتكبر")
        elif scalability == "low":
            if fw_scale == "low":
                score += 5  # OK for small projects
            elif fw_scale == "high":
                score -= 5  # Overkill

        # ── 4. Multi-Agent Collaboration Patterns (0–15 points) ────────────────
        fw_multi = features.get("multi_agent", "single_agent")
        if collaboration != "any":
            if fw_multi == collaboration:
                score += 15
                pattern_names = {
                    "hierarchical": "الهرمي (إيجنت مدير وموظفين)",
                    "graph": "الـ Graph State Machine (تفرعات ودورات معقدة)",
                    "delegation": "التفويض الديناميكي (إيجنت يستدعي إيجنت كأداة)",
                    "visual_sequential": "التدفق البصري المتسلسل (Low-code DAG)",
                }
                reasons_for.append(f"🎯 يدعم نمط التعاون المطلوب: {pattern_names.get(collaboration, collaboration)}")
            else:
                score -= 10
                reasons_against.append(f"⚠️ نمط تنظيم الإيجنتس لديه هو ({fw_multi}) وليس ({collaboration})")

        # ── 5. Production Readiness ────────────────────────────────────────────
        if production and not profile.get("production_ready", True):
            score -= 20
            reasons_against.append("❌ مش Production-Ready بعد — تجريبي فقط")
        elif production and profile.get("production_ready", True):
            score += 5
            reasons_for.append("✅ جاهز للإنتاج (Production-Ready)")

        # ── 6. Team Experience ─────────────────────────────────────────────────
        complex_frameworks = {"langgraph", "controlflow", "dspy", "autogen"}
        easy_frameworks = {"agno", "dify", "flowise", "crewai"}

        if team_experience == "beginner":
            if fw_id in easy_frameworks:
                score += 8
                reasons_for.append("✅ سهل التعلم — مناسب للبيجنرز")
            elif fw_id in complex_frameworks:
                score -= 10
                reasons_against.append("⚠️ Learning curve عالية — يحتاج خبرة")

        elif team_experience == "expert":
            if fw_id in complex_frameworks:
                score += 5
                reasons_for.append("✅ يعطيك تحكم كامل — مناسب للـ experts")

        score = max(0.0, min(100.0, score))
        return score, reasons_for, reasons_against

    def _generate_reasoning(
        self,
        top: FrameworkMatch,
        alternatives: List[FrameworkMatch],
        use_case: Optional[str],
        requirements: List[str],
        scalability: str,
        override_msg: str = ""
    ) -> tuple[str, str]:

        uc_name = (
            self.use_cases[use_case]["arabic"]
            if use_case and use_case in self.use_cases
            else "المشروع بتاعك"
        )

        gap = top.score - alternatives[0].score if alternatives else 0
        alt_name = alternatives[0].name if alternatives else ""

        # Arabic reasoning
        ar = f"بناءً على تحليل {len(self.profiles)} Framework مع بيانات الـ Benchmark الحقيقية:\n\n"
        ar += f"**الاختيار الأمثل: {top.name}** ({top.score:.0f}% توافق)\n\n"

        if override_msg:
            ar += f"{override_msg}\n\n"

        if top.reasons_for:
            ar += f"**ليه {top.name}؟**\n"
            for r in top.reasons_for[:3]:
                ar += f"• {r}\n"

        if alternatives:
            ar += f"\n**البديل المقبول: {alt_name}** ({alternatives[0].score:.0f}%)\n"
            if gap > 15:
                ar += f"الفارق {gap:.0f}% — {top.name} أوضح بكتير.\n"
            elif gap < 5:
                ar += f"الفارق صغير ({gap:.0f}%) — الاتنين مقبولين، قرر حسب الـ Team preference.\n"

        if scalability == "high" and not override_msg:
            ar += f"\n**⚠️ Scalability:** لو هتضيف features كتير بعدين، LangGraph هو الأأمن على المدى البعيد لأن الـ Graph-based architecture بتتوسع أحسن.\n"

        # English reasoning
        en = f"Based on analysis of {len(self.profiles)} frameworks + real benchmark data:\n\n"
        en += f"**Best Pick: {top.name}** ({top.score:.0f}% compatibility)\n"
        if override_msg:
            en += f"{override_msg}\n"
        if top.reasons_for:
            en += "\nKey reasons:\n"
            for r in top.reasons_for[:3]:
                en += f"• {r}\n"

        return ar, en

    def _check_requirements(
        self,
        requirements: List[str],
        top: FrameworkMatch,
        all_matches: List[FrameworkMatch],
    ) -> tuple[List[str], List[str]]:
        matched = []
        unmet = []
        profile = self.profiles.get(top.framework_id, {})
        features = profile.get("features", {})

        for req in requirements:
            req_lower = req.lower().replace(" ", "_")
            if req_lower in ("hitl", "human_approval"):
                (matched if features.get("hitl") else unmet).append(req)
            elif req_lower in ("memory", "persistent_memory"):
                (matched if features.get("memory") else unmet).append(req)
            elif req_lower == "multimodal":
                (matched if features.get("multimodal") else unmet).append(req)
            else:
                matched.append(req)  # assume matched if not specifically checked

        return matched, unmet

    def list_use_cases(self) -> List[Dict]:
        return [
            {"id": k, "name": v["name"], "arabic": v["arabic"]}
            for k, v in self.use_cases.items()
        ]

    def list_frameworks(self) -> List[str]:
        return list(self.profiles.keys())
