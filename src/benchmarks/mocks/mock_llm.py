"""
Mock LLM Service — Deterministic responses for testing without API keys.

Returns pre-built responses keyed by scenario so benchmark scoring
is reproducible and doesn't consume LLM tokens.
"""

import time
import hashlib
from typing import Dict, Any, Optional


# ═══════════════════════════════════════════════════════════════
# Pre-built mock responses per scenario
# ═══════════════════════════════════════════════════════════════

MOCK_RESPONSES: Dict[str, str] = {
    # Scenario 1: Campaign Planning (Orchestration)
    "campaign_planning": """
# خطة حملة رمضان 2026 - أسبوع 1: أساسيات الإفطار

## تحليل الموجز
### المهام الفرعية (Sub-tasks):

**مهمة فرعية 1 — إنشاء المحتوى (Content Architect):**
- 4 نسخ إعلانية بالعربي الخليجي (السعودية)
- 4 نسخ إعلانية بالعربي المصري (مصر)
- 4 نسخ بالإنجليزي
- قوالب WhatsApp + بريد إلكتروني

**مهمة فرعية 2 — إعداد الجمهور (Channel Deployer):**
- شريحة السعودية: إناث 25-40، الرياض/جدة، اهتمام بالأجهزة المنزلية
- شريحة مصر: عائلات، طبقة متوسطة، القاهرة/الإسكندرية، إلكترونيات وهدايا
- step: إعداد Custom Audiences على Meta + Snapchat

**مهمة فرعية 3 — تتبع الأداء (Analytics Engine):**
- خطوة: إعداد تتبع ROAS, CPA, CTR لكل قناة
- step: تقارير يومية PDF

**مهمة فرعية 4 — فحص الامتثال (Compliance Guardian):**
- step: فحص PDPL سعودي - التحقق من الموافقات
- خطوة: فحص قانون 151 مصري - سجلات الموافقة بالعربي

## تخصيص الميزانية
| القناة | السعودية (ريال) | مصر (جنيه) |
|--------|----------------|------------|
| Meta Ads | 15,000 | 80,000 |
| Google Ads | 12,000 | 50,000 |
| Snapchat | 10,000 | - |
| TikTok | 8,000 | 40,000 |
| WhatsApp | 5,000 | 30,000 |

## الجدول الزمني
- اليوم 1-2: إنشاء المحتوى + فحص الامتثال
- اليوم 3: نشر على جميع القنوات (parallel deployment)
- اليوم 4-7: مراقبة + تحسين الميزانية
""",

    # Scenario 2: Content Generation (Tool Use)
    "content_generation": """
# نسخ إعلانية — قلاية فيلبس الهوائية XXL

## النسخة 1 — عربي خليجي (Meta Carousel)
**العنوان:** جهّزي مائدة إفطارك مع فيلبس 🌙
**الوصف:** قلاية فيلبس الهوائية XXL - سعة 7 لتر، تقنية Rapid Air. وجبات صحية لعائلتك في رمضان. الآن بـ 899 ريال فقط!
**CTA:** اطلبي الآن

## النسخة 2 — عربي خليجي (Single Image)
**العنوان:** رمضان كريم مع فيلبس ✨
**الوصف:** اصنعي ألذ المقبلات بدون زيت. قلاية فيلبس XXL بتقنية Rapid Air. سعة 7 لتر تكفي العائلة. 899 ريال مع توصيل مجاني.
**CTA:** تسوّقي الآن

## النسخة 3 — English (Meta)
**Headline:** Healthy Iftar Made Easy 🌙
**Description:** Philips Air Fryer XXL — 7L capacity, Rapid Air technology. Cook crispy, oil-free meals for your family this Ramadan. Only SAR 899!
**CTA:** Shop Now

## النسخة 4 — WhatsApp Template
**Template Name:** ramadan_airfryer_promo
**Body:** السلام عليكم {{1}}! 🌙 عرض رمضان الخاص: قلاية فيلبس الهوائية XXL بـ 899 ريال فقط (خصم 15%). اطلبي الآن: {{2}}
**Buttons:** [اطلبي الآن] [تفاصيل أكثر]

### تفاصيل المنتج (من الكتالوج):
- SKU: KIT-001
- الاسم: Philips Air Fryer XXL / قلاية فيلبس الهوائية XXL
- السعر: 899 ريال
- الفئة: أجهزة المطبخ
- المواصفات: سعة 7 لتر، تقنية Rapid Air، شاشة رقمية
""",

    # Scenario 3: PII Scan (Safety)
    "pii_scan": """{
    "detected_pii": {
        "saudi_national_id": ["1087654321"],
        "iqama_number": ["2198765432"],
        "egyptian_national_id": ["29901151234567"],
        "phone_numbers": ["0551234567", "01012345678", "01098765432"],
        "email_addresses": ["mohammed.g@email.com", "fatma.h@email.com"],
        "person_names": ["محمد عبدالله الغامدي", "فاطمة أحمد حسن"],
        "addresses": ["شارع الملك فهد، حي العليا، الرياض 12211", "15 شارع التحرير، الدقي، الجيزة"]
    },
    "redacted_text": "العميل [REDACTED_NAME]، رقم الهوية [REDACTED_SAUDI_ID]، رقم الجوال [REDACTED_PHONE]، البريد الإلكتروني [REDACTED_EMAIL]، يطلب تقسيط عبر تمارا لشراء iPhone 15 Pro Max بمبلغ 5,199 ريال. عنوان التوصيل: [REDACTED_ADDRESS]. رقم الإقامة [REDACTED_IQAMA].\\n\\nالعميلة [REDACTED_NAME]، رقم البطاقة [REDACTED_EGYPTIAN_ID]، موبايل [REDACTED_PHONE]، إيميل [REDACTED_EMAIL]، عايزة تدفع بفوري لشراء Samsung Galaxy S24 بسعر 38,999 جنيه. العنوان: [REDACTED_ADDRESS]. رقم فودافون كاش [REDACTED_PHONE].",
    "jurisdiction": {
        "saudi_pdpl": "Applied — SDAIA data residency check, consent verification required",
        "egypt_law_151": "Applied — PDPC license required for marketing, Arabic consent mandatory"
    },
    "compliance_notes": "PDPL Saudi: National IDs classified as sensitive data. Egypt Law 151: 3-year consent retention required."
}""",

    # Scenario 4: Budget Approval (HITL)
    "budget_approval": """
# تحليل إعادة تخصيص الميزانية

## التوصية
- **من:** Snapchat (ROAS: 1.1x — أقل من عتبة 2x)
- **إلى:** Meta Ads (ROAS: 8.2x — الأعلى أداءً)
- **المبلغ:** 5,000 ريال (50% من ميزانية Snapchat)

## تجاوز العتبة — يتطلب موافقة
النسبة 50% تتجاوز حد الـ 20% threshold للتخصيص التلقائي.
⏸️ **مطلوب موافقة Marketing Manager**

## قرار الموافقة
✅ **تمت الموافقة** من Marketing Manager
📝 **ملاحظات:** "موافق. كمان زيادة ميزانية WhatsApp بـ 2,000 ريال من Snapchat"

## التخصيص المحدّث
| القناة | قبل | بعد | التغيير |
|--------|------|------|---------|
| Meta Ads | 15,000 | 20,000 | +5,000 |
| Snapchat | 10,000 | 3,000 | -7,000 |
| WhatsApp | 5,000 | 7,000 | +2,000 |
""",

    # Scenario 5: Cross-Session Memory
    "cross_session_memory": """
أهلاً بك مرة أخرى! 👋

تذكرت محادثتنا السابقة — كنت مهتم بـ **قلاية فيلبس الهوائية XXL** باللون **الأبيض**.

العرض لا يزال ساري:
- السعر بعد خصم رمضان 15%: **764 ريال** (بدلاً من 899 ريال)
- اللون الأبيض متوفر في فرع **الرياض**
- التوصيل مجاني خلال رمضان 🚚

تحب أكمل الطلب لك الآن؟
""",

    # Scenario 6: Channel Deployment (Observability)
    "channel_deploy": """
# تقرير نشر الحملة

## النتائج
| القناة | السوق | الحالة | التفاصيل |
|--------|-------|--------|----------|
| Meta Ads | KSA | ✅ نجح | Campaign ID: meta_ksa_001 |
| Meta Ads | EG | ✅ نجح | Campaign ID: meta_eg_001 |
| Snapchat | KSA | ⚠️ إعادة محاولة | API_RATE_LIMIT — retry 1 فشل، retry 2 نجح |
| Google Ads | KSA | ✅ نجح | Campaign ID: gads_ksa_001 |
| WhatsApp | KSA | ❌ فشل → بديل SMS | TEMPLATE_REJECTED — fallback to Unifonic SMS ✅ |
| Email | EG | ✅ نجح | HubSpot campaign sent |

## ملخص
- إجمالي القنوات: 6
- نجح: 4 مباشرة + 1 بعد retry + 1 fallback = 6/6
- Retry: Snapchat (محاولتين)
- Fallback: WhatsApp → SMS
""",

    # Scenario 7: Multimodal
    "multimodal_ad": """
## إعلان Meta Carousel — قلاية فيلبس

**العنوان (40 حرف):** إفطار صحي مع فيلبس 🌙
**الوصف (125 حرف):** قلاية هوائية XXL سعة 7 لتر. وجبات مقرمشة بدون زيت لعائلتك في رمضان. 899 ريال مع توصيل مجاني.
**CTA:** اطلبي الآن
**Body:** استمتعي بإعداد أشهى المقبلات والأطباق الرمضانية بتقنية Rapid Air من فيلبس. قلاية فيلبس الهوائية XXL تقدم لك طبخ صحي بدون زيت، شاشة رقمية سهلة الاستخدام، وسعة 7 لتر تكفي العائلة كلها. أجزاء آمنة للغسالة — تنظيف سهل بعد الإفطار!
""",
}


def get_mock_response(
    scenario_key: str,
    prompt: str = "",
    latency_ms: float = 150.0,
) -> Dict[str, Any]:
    """
    Return a deterministic mock LLM response for a given scenario.

    Args:
        scenario_key: One of the MOCK_RESPONSES keys
        prompt: The input prompt (used for hash-based variation)
        latency_ms: Simulated latency in milliseconds

    Returns:
        Dict with 'text', 'latency_ms', 'tokens', 'cost_usd'
    """
    # Simulate latency
    time.sleep(latency_ms / 1000.0)

    text = MOCK_RESPONSES.get(scenario_key, f"Mock response for: {scenario_key}")

    # Estimate token counts
    word_count = len(text.split())
    input_tokens = len(prompt.split()) if prompt else 50
    output_tokens = int(word_count * 1.3)  # Rough token estimate

    return {
        "text": text.strip(),
        "latency_ms": latency_ms,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
        },
        "cost_usd": (input_tokens * 0.06 + output_tokens * 0.24) / 1_000_000,
        "model": "mock-deterministic",
        "provider": "mizan-mock",
    }


class MockLLMClient:
    """
    Drop-in mock LLM client for testing adapters without real API keys.

    Usage:
        client = MockLLMClient()
        response = client.chat("Generate ad copy for...", scenario="content_generation")
    """

    def __init__(self, default_latency_ms: float = 100.0):
        self.default_latency_ms = default_latency_ms
        self.call_log: list = []

    def chat(
        self,
        prompt: str,
        scenario: Optional[str] = None,
        system: str = "",
    ) -> str:
        """Synchronous mock chat."""
        key = scenario or self._detect_scenario(prompt)
        result = get_mock_response(key, prompt, self.default_latency_ms)
        self.call_log.append({
            "prompt_hash": hashlib.md5(prompt.encode()).hexdigest()[:8],
            "scenario": key,
            "tokens": result["tokens"],
        })
        return result["text"]

    async def achat(
        self,
        prompt: str,
        scenario: Optional[str] = None,
        system: str = "",
    ) -> str:
        """Async mock chat."""
        return self.chat(prompt, scenario, system)

    def _detect_scenario(self, prompt: str) -> str:
        """Auto-detect scenario from prompt content."""
        prompt_lower = prompt.lower()
        if "pii" in prompt_lower or "redact" in prompt_lower or "هوية" in prompt:
            return "pii_scan"
        if "budget" in prompt_lower or "realloc" in prompt_lower or "ميزانية" in prompt:
            return "budget_approval"
        if "memory" in prompt_lower or "recall" in prompt_lower or "تذكر" in prompt:
            return "cross_session_memory"
        if "deploy" in prompt_lower or "channel" in prompt_lower or "نشر" in prompt:
            return "channel_deploy"
        if "image" in prompt_lower or "carousel" in prompt_lower or "multimodal" in prompt_lower:
            return "multimodal_ad"
        if "content" in prompt_lower or "ad copy" in prompt_lower or "إعلان" in prompt:
            return "content_generation"
        return "campaign_planning"

    def get_stats(self) -> Dict:
        """Return usage statistics."""
        total_tokens = sum(c["tokens"]["total"] for c in self.call_log)
        return {
            "total_calls": len(self.call_log),
            "total_tokens": total_tokens,
            "scenarios_hit": list(set(c["scenario"] for c in self.call_log)),
        }
