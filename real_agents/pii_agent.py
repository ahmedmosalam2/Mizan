"""
PII Detection Agent — Real LLM-based PII detection for Arabic text.

This agent does TWO passes:
1. Regex pass: Fast, deterministic pattern matching
2. LLM pass: Understands context, catches what regex misses

Then we compare: Did the LLM add value over regex? Was it worth the cost?
"""

import re
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from real_agents.llm_client import LLMClient


# ── Regex Patterns (Baseline) ────────────────────────────────────

REGEX_PATTERNS = {
    "saudi_national_id": re.compile(r"\b[12]\d{9}\b"),
    "egyptian_national_id": re.compile(r"\b[23]\d{13}\b"),
    "phone_sa": re.compile(r"(?:\+966|00966|0)?5\d[\s\-]?\d{3}[\s\-]?\d{4}"),
    "phone_eg": re.compile(r"(?:\+20|0020|0)?1[0-2]\d[\s\-]?\d{3}[\s\-]?\d{4}"),
    "email": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "iban": re.compile(r"\b(?:SA|EG)\d{2}[A-Z0-9]{4,30}\b"),
}


# ── Test Corpus ──────────────────────────────────────────────────

TEST_TEXTS = [
    {
        "id": "simple_saudi",
        "text": "العميل أحمد محمد، رقم الهوية 1234567890، يريد استرجاع المنتج.",
        "expected_pii": {"saudi_national_id": ["1234567890"], "person_name": ["أحمد محمد"]},
        "difficulty": "easy",
    },
    {
        "id": "mixed_sa_eg",
        "text": (
            "الطلب رقم #4521 — العميلة فاطمة الزهراء (هوية: 2987654321) طلبت شحن "
            "لعنوان الرياض. التواصل على 0551234567 أو fatima.z@email.com. "
            "وفي مصر، العميل محمود حسن (رقم قومي: 29901011234567) "
            "عنوانه القاهرة والتليفون 01012345678."
        ),
        "expected_pii": {
            "saudi_national_id": ["2987654321"],
            "egyptian_national_id": ["29901011234567"],
            "phone_sa": ["0551234567"],
            "phone_eg": ["01012345678"],
            "email": ["fatima.z@email.com"],
            "person_name": ["فاطمة الزهراء", "محمود حسن"],
        },
        "difficulty": "medium",
    },
    {
        "id": "hidden_pii",
        "text": (
            "العميل قال رقمه واحد اتنين تلاتة اربعة خمسة ستة سبعة تمانية تسعة صفر "
            "وعايز يتواصل على الرقم ده خمسة خمسة واحد اتنين تلاتة اربعة خمسة ستة سبعة"
        ),
        "expected_pii": {
            "hidden_national_id": ["1234567890"],
            "hidden_phone": ["0551234567"],
        },
        "difficulty": "hard",
        "note": "PII written as Arabic words instead of digits — regex will MISS this",
    },
    {
        "id": "no_pii_clean",
        "text": "عروض رمضان على أجهزة آيفون ١٥ برو. خصم ٢٠٪ لفترة محدودة. تسوق الآن من أقرب فرع.",
        "expected_pii": {},
        "difficulty": "easy",
        "note": "Clean text — no PII. Agent should return nothing.",
    },
    {
        "id": "context_dependent",
        "text": (
            "أرسل العميل صورة من بطاقته الشخصية عبر الواتساب للتحقق من هويته. "
            "الصورة تحتوي على الاسم: خالد العتيبي، ورقم الهوية المدون عليها."
        ),
        "expected_pii": {
            "person_name": ["خالد العتيبي"],
            "id_image_reference": ["صورة من بطاقته الشخصية"],
        },
        "difficulty": "hard",
        "note": "References PII in an image — no actual digits but still a privacy risk",
    },
]


# ── PII Agent Prompt ─────────────────────────────────────────────

PII_AGENT_PROMPT = """أنت Compliance Guardian — خبير كشف البيانات الشخصية (PII) في النصوص العربية.

## مهمتك
افحص النص المعطى واكتشف أي بيانات شخصية (PII) موجودة فيه.

## أنواع PII المطلوب كشفها
1. **رقم الهوية السعودي**: 10 أرقام يبدأ بـ 1 أو 2
2. **الرقم القومي المصري**: 14 رقم
3. **أرقام الهاتف**: سعودية (+966/05xx) ومصرية (+20/01xx)
4. **البريد الإلكتروني**: أي عنوان بريد
5. **IBAN**: أرقام حسابات بنكية
6. **أسماء أشخاص**: أسماء مذكورة في السياق
7. **PII مخفية**: أرقام مكتوبة بالحروف العربية (مثل "واحد اتنين تلاتة")
8. **إشارات لـ PII**: ذكر إرسال صور هوية أو وثائق شخصية

## قواعد مهمة
- اكتشف PII حتى لو مكتوبة بالحروف مش بالأرقام
- اكتشف إشارات لوثائق شخصية (صور هوية، جواز سفر)
- لا تعتبر أسماء المنتجات أو الشركات كـ PII
- لا تعتبر الأسعار أو أرقام الطلبات كـ PII

## شكل الإخراج (JSON)
{
    "pii_found": true/false,
    "items": [
        {
            "type": "saudi_national_id|egyptian_national_id|phone|email|iban|person_name|hidden_pii|pii_reference",
            "value": "القيمة المكتشفة",
            "context": "الجملة اللي فيها الـ PII",
            "risk_level": "critical|high|medium|low",
            "confidence": 0.0-1.0
        }
    ],
    "risk_summary": "ملخص المخاطر",
    "redacted_text": "النص بعد إخفاء البيانات الشخصية"
}"""


# ── Results ──────────────────────────────────────────────────────

@dataclass
class PIIMatch:
    """Single PII match."""
    pii_type: str
    value: str
    source: str  # "regex" or "llm"
    confidence: float = 1.0


@dataclass
class PIIResult:
    """Result from PII detection on one text."""
    text_id: str
    difficulty: str
    regex_matches: List[PIIMatch] = field(default_factory=list)
    llm_matches: List[PIIMatch] = field(default_factory=list)
    llm_raw_output: str = ""
    llm_parsed: Optional[Dict] = None
    expected_pii: Dict = field(default_factory=dict)
    regex_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    llm_stats: Optional[Dict] = None

    @property
    def llm_added_value(self) -> List[str]:
        """What did the LLM find that regex missed?"""
        regex_types = {m.pii_type for m in self.regex_matches}
        return [m.value for m in self.llm_matches if m.pii_type not in regex_types]

    def summary(self) -> str:
        lines = [
            f"\n{'='*60}",
            f"📝 Text: {self.text_id} (difficulty: {self.difficulty})",
            f"{'='*60}",
            f"🔍 Regex: {len(self.regex_matches)} matches in {self.regex_time_ms:.1f}ms",
        ]
        for m in self.regex_matches:
            lines.append(f"   • [{m.pii_type}] {m.value}")

        lines.append(f"🤖 LLM: {len(self.llm_matches)} matches in {self.llm_time_ms:.1f}ms")
        for m in self.llm_matches:
            lines.append(f"   • [{m.pii_type}] {m.value} (confidence: {m.confidence:.0%})")

        added = self.llm_added_value
        if added:
            lines.append(f"✨ LLM added value: {added}")
        else:
            lines.append(f"➖ LLM added nothing new over regex")

        if self.llm_stats:
            lines.append(f"💰 LLM cost: ${self.llm_stats.get('total_cost_usd', 0):.6f} | {self.llm_stats.get('total_tokens', 0)} tokens")

        return "\n".join(lines)


def regex_scan(text: str) -> List[PIIMatch]:
    """Fast regex-based PII scan."""
    matches = []
    for pii_type, pattern in REGEX_PATTERNS.items():
        for m in pattern.finditer(text):
            matches.append(PIIMatch(
                pii_type=pii_type,
                value=m.group(),
                source="regex",
            ))
    return matches


def run_pii_agent(
    client: LLMClient,
    text: str,
    text_id: str = "unknown",
    difficulty: str = "unknown",
    expected_pii: Optional[Dict] = None,
) -> PIIResult:
    """
    Run PII detection: regex first, then LLM, then compare.
    """
    result = PIIResult(
        text_id=text_id,
        difficulty=difficulty,
        expected_pii=expected_pii or {},
    )

    # Pass 1: Regex
    start = time.time()
    result.regex_matches = regex_scan(text)
    result.regex_time_ms = (time.time() - start) * 1000

    # Pass 2: LLM
    client.reset_stats()
    start = time.time()

    try:
        raw = client.chat(
            user_message=f"افحص هذا النص واكتشف أي بيانات شخصية:\n\n{text}",
            system_prompt=PII_AGENT_PROMPT,
            temperature=0.1,  # Low temperature for deterministic detection
        )
        result.llm_time_ms = (time.time() - start) * 1000
        result.llm_raw_output = raw

        # Parse LLM response
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()
                if clean.startswith("json"):
                    clean = clean[4:].strip()

            parsed = json.loads(clean)
            result.llm_parsed = parsed

            for item in parsed.get("items", []):
                result.llm_matches.append(PIIMatch(
                    pii_type=item.get("type", "unknown"),
                    value=item.get("value", ""),
                    source="llm",
                    confidence=float(item.get("confidence", 0.8)),
                ))

        except (json.JSONDecodeError, ValueError):
            # Try to extract JSON
            json_start = raw.find("{")
            json_end = raw.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                try:
                    parsed = json.loads(raw[json_start:json_end])
                    result.llm_parsed = parsed
                    for item in parsed.get("items", []):
                        result.llm_matches.append(PIIMatch(
                            pii_type=item.get("type", "unknown"),
                            value=item.get("value", ""),
                            source="llm",
                            confidence=float(item.get("confidence", 0.8)),
                        ))
                except (json.JSONDecodeError, ValueError):
                    pass

    except Exception as exc:
        result.llm_raw_output = f"ERROR: {exc}"
        result.llm_time_ms = (time.time() - start) * 1000

    result.llm_stats = client.stats.summary()
    return result


def run_pii_benchmark(client: LLMClient) -> List[PIIResult]:
    """Run PII detection on all test texts and return results."""
    results = []
    for test in TEST_TEXTS:
        r = run_pii_agent(
            client=client,
            text=test["text"],
            text_id=test["id"],
            difficulty=test["difficulty"],
            expected_pii=test.get("expected_pii", {}),
        )
        results.append(r)
    return results
