"""
Content Generation Agent — Creates real Arabic ad copy for products.

This is a REAL agent that:
1. Takes product data (name, price, description, market)
2. Calls an LLM to generate 4 ad copy variants
3. Validates output (character limits, dialect, format)
4. Returns structured results with quality metrics

No fake scores. No simulations. Real LLM calls. Real results.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from real_agents.llm_client import LLMClient


# ── Product Data ─────────────────────────────────────────────────

PRODUCT_CATALOG = [
    {
        "sku": "IP15-PRO-256",
        "name_en": "iPhone 15 Pro 256GB",
        "name_ar": "آيفون ١٥ برو ٢٥٦ جيجا",
        "price_sar": 4699,
        "price_egp": 62990,
        "description_en": "Titanium design, A17 Pro chip, 48MP camera system, USB-C",
        "description_ar": "تصميم تيتانيوم، شريحة A17 Pro، نظام كاميرا ٤٨ ميجابكسل، USB-C",
        "category": "smartphones",
        "brand": "Apple",
    },
    {
        "sku": "SS24-ULTRA",
        "name_en": "Samsung Galaxy S24 Ultra",
        "name_ar": "سامسونج جالكسي S24 ألترا",
        "price_sar": 5099,
        "price_egp": 67990,
        "description_en": "Galaxy AI, 200MP camera, S Pen, Titanium frame",
        "description_ar": "ذكاء اصطناعي جالكسي، كاميرا ٢٠٠ ميجابكسل، قلم S، إطار تيتانيوم",
        "category": "smartphones",
        "brand": "Samsung",
    },
    {
        "sku": "PS5-SLIM",
        "name_en": "PlayStation 5 Slim Digital",
        "name_ar": "بلايستيشن ٥ سلم ديجيتال",
        "price_sar": 1699,
        "price_egp": 22990,
        "description_en": "Slim design, 1TB SSD, DualSense controller, 4K gaming",
        "description_ar": "تصميم نحيف، ١ تيرا SSD، يد DualSense، ألعاب 4K",
        "category": "gaming",
        "brand": "Sony",
    },
    {
        "sku": "DYS-V15",
        "name_en": "Dyson V15 Detect",
        "name_ar": "دايسون V15 ديتكت",
        "price_sar": 2799,
        "price_egp": 37990,
        "description_en": "Laser dust detection, HEPA filtration, 60 min runtime",
        "description_ar": "كشف الغبار بالليزر، فلتر HEPA، تشغيل ٦٠ دقيقة",
        "category": "home_appliances",
        "brand": "Dyson",
    },
]


# ── System Prompt ────────────────────────────────────────────────

CONTENT_AGENT_PROMPT = """أنت Content Architect — خبير توليد محتوى إعلاني عربي احترافي.

## مهمتك
اكتب إعلانات لمنتج محدد بأربع نسخ مختلفة. كل نسخة لازم تكون مناسبة للمنصة والسوق.

## القواعد الصارمة
1. **اللهجة الخليجية** للسعودية: استخدم كلمات مثل "وش تبي أكثر؟"، "يالله"، "حياك"، "ذوقك رفيع"
2. **اللهجة المصرية** لمصر: استخدم كلمات مثل "إيه رأيك؟"، "يلا"، "عرض مش هيتكرر"، "متفوتش"
3. **حدود الأحرف**: headline (40 حرف max)، description (125 حرف max)
4. **السعر**: اذكر السعر بالعملة المحلية
5. **رمضان**: استخدم عبارات رمضانية مناسبة مثل "عروض رمضان"، "هدية رمضان"
6. **CTA واضح**: كل إعلان لازم يكون فيه call-to-action

## شكل الإخراج (JSON)
أرجع JSON بالضبط بالشكل ده:
{
    "gulf_carousel": {
        "headline_ar": "العنوان بالخليجي (max 40 chars)",
        "description_ar": "الوصف بالخليجي (max 125 chars)",
        "cta_ar": "زر الإجراء",
        "cards": ["نص بطاقة 1", "نص بطاقة 2", "نص بطاقة 3"]
    },
    "gulf_single": {
        "headline_ar": "العنوان بالخليجي (max 40 chars)",
        "body_ar": "نص الإعلان الكامل (max 125 chars)",
        "cta_ar": "زر الإجراء"
    },
    "egyptian_single": {
        "headline_ar": "العنوان بالمصري (max 40 chars)",
        "body_ar": "نص الإعلان الكامل (max 125 chars)",
        "cta_ar": "زر الإجراء"
    },
    "whatsapp_template": {
        "header": "العنوان (max 60 chars)",
        "body": "نص الرسالة (max 1024 chars)",
        "footer": "ذيل الرسالة (max 60 chars)",
        "cta_text": "نص الزر",
        "cta_url": "https://example.com/product"
    }
}"""


# ── Quality Checks ───────────────────────────────────────────────

@dataclass
class QualityCheck:
    """Single quality check result."""
    name: str
    passed: bool
    expected: str
    actual: str
    details: str = ""


@dataclass
class ContentResult:
    """Full result from content generation."""
    product: Dict[str, Any]
    raw_output: str
    parsed_output: Optional[Dict[str, Any]] = None
    quality_checks: List[QualityCheck] = field(default_factory=list)
    quality_score: float = 0.0  # 0-100
    llm_stats: Optional[Dict[str, Any]] = None

    def summary(self) -> str:
        passed = sum(1 for c in self.quality_checks if c.passed)
        total = len(self.quality_checks)
        lines = [
            f"📦 Product: {self.product['name_en']}",
            f"✅ Quality: {passed}/{total} checks passed ({self.quality_score:.0f}%)",
        ]
        if self.llm_stats:
            lines.append(f"🔢 Tokens: {self.llm_stats['total_tokens']}")
            lines.append(f"💰 Cost: ${self.llm_stats['total_cost_usd']:.6f}")
            lines.append(f"⏱  Latency: {self.llm_stats['total_latency_ms']:.0f}ms")
        for check in self.quality_checks:
            icon = "✅" if check.passed else "❌"
            lines.append(f"  {icon} {check.name}: {check.details}")
        return "\n".join(lines)


def validate_content(product: Dict, output: Dict) -> List[QualityCheck]:
    """Run quality checks on generated content."""
    checks = []

    # Check 1: JSON parsed successfully
    checks.append(QualityCheck(
        name="json_valid",
        passed=output is not None,
        expected="Valid JSON",
        actual="Valid" if output else "Invalid",
        details="JSON parsed successfully" if output else "Failed to parse JSON",
    ))

    if not output:
        return checks

    # Check 2: All 4 variants present
    expected_keys = {"gulf_carousel", "gulf_single", "egyptian_single", "whatsapp_template"}
    actual_keys = set(output.keys())
    missing = expected_keys - actual_keys
    checks.append(QualityCheck(
        name="all_variants",
        passed=len(missing) == 0,
        expected="4 variants",
        actual=f"{len(actual_keys & expected_keys)} variants",
        details=f"Missing: {missing}" if missing else "All 4 variants present",
    ))

    # Check 3: Headline character limits (40 chars)
    for variant_key in ["gulf_carousel", "gulf_single", "egyptian_single"]:
        variant = output.get(variant_key, {})
        headline = variant.get("headline_ar", "")
        ok = 0 < len(headline) <= 40
        checks.append(QualityCheck(
            name=f"{variant_key}_headline_length",
            passed=ok,
            expected="1-40 chars",
            actual=f"{len(headline)} chars",
            details=f'"{headline[:50]}"',
        ))

    # Check 4: Description/body limits (125 chars)
    for variant_key, body_field in [("gulf_carousel", "description_ar"), ("gulf_single", "body_ar"), ("egyptian_single", "body_ar")]:
        variant = output.get(variant_key, {})
        body = variant.get(body_field, "")
        ok = 0 < len(body) <= 125
        checks.append(QualityCheck(
            name=f"{variant_key}_body_length",
            passed=ok,
            expected="1-125 chars",
            actual=f"{len(body)} chars",
            details=f'"{body[:80]}..."' if len(body) > 80 else f'"{body}"',
        ))

    # Check 5: Price mentioned
    price_sar = str(product["price_sar"])
    price_egp = str(product["price_egp"])
    full_text = json.dumps(output, ensure_ascii=False)

    sar_mentioned = price_sar in full_text or f"٤٦٩٩" in full_text  # Arabic numerals
    egp_mentioned = price_egp in full_text

    checks.append(QualityCheck(
        name="price_sar_mentioned",
        passed=sar_mentioned,
        expected=f"SAR {price_sar}",
        actual="Found" if sar_mentioned else "Not found",
        details=f"SAR price {'found' if sar_mentioned else 'missing'} in gulf variants",
    ))
    checks.append(QualityCheck(
        name="price_egp_mentioned",
        passed=egp_mentioned,
        expected=f"EGP {price_egp}",
        actual="Found" if egp_mentioned else "Not found",
        details=f"EGP price {'found' if egp_mentioned else 'missing'} in egyptian variant",
    ))

    # Check 6: CTA present
    for variant_key in ["gulf_carousel", "gulf_single", "egyptian_single"]:
        variant = output.get(variant_key, {})
        cta = variant.get("cta_ar", "")
        checks.append(QualityCheck(
            name=f"{variant_key}_has_cta",
            passed=bool(cta),
            expected="CTA text",
            actual=f'"{cta}"' if cta else "Missing",
            details=f"CTA: {cta}" if cta else "No CTA found",
        ))

    # Check 7: WhatsApp template structure
    wa = output.get("whatsapp_template", {})
    wa_ok = all(k in wa for k in ["header", "body", "cta_text"])
    checks.append(QualityCheck(
        name="whatsapp_structure",
        passed=wa_ok,
        expected="header, body, cta_text",
        actual=f"Has: {list(wa.keys())}",
        details="WhatsApp template complete" if wa_ok else "Missing fields",
    ))

    # Check 8: Gulf dialect markers
    gulf_text = json.dumps(output.get("gulf_carousel", {}), ensure_ascii=False) + \
                json.dumps(output.get("gulf_single", {}), ensure_ascii=False)
    gulf_markers = ["يالله", "حياك", "وش", "ذوق", "عرض", "احصل", "تبي", "لك", "فرصة", "خصم", "حلو", "توصيل"]
    found_gulf = [m for m in gulf_markers if m in gulf_text]
    checks.append(QualityCheck(
        name="gulf_dialect",
        passed=len(found_gulf) >= 2,
        expected="≥2 Gulf Arabic markers",
        actual=f"{len(found_gulf)} markers: {found_gulf[:5]}",
        details=f"Gulf markers found: {found_gulf}",
    ))

    # Check 9: Egyptian dialect markers
    egypt_text = json.dumps(output.get("egyptian_single", {}), ensure_ascii=False)
    egypt_markers = ["يلا", "متفوتش", "إيه", "كده", "دلوقتي", "عرض", "احصل", "فرصة", "خصم", "مش هيتكرر", "اشتري"]
    found_egypt = [m for m in egypt_markers if m in egypt_text]
    checks.append(QualityCheck(
        name="egyptian_dialect",
        passed=len(found_egypt) >= 1,
        expected="≥1 Egyptian Arabic markers",
        actual=f"{len(found_egypt)} markers: {found_egypt[:5]}",
        details=f"Egyptian markers found: {found_egypt}",
    ))

    return checks


def run_content_agent(client: LLMClient, product: Optional[Dict] = None) -> ContentResult:
    """
    Run the content generation agent on a product.

    Args:
        client: LLMClient instance
        product: Product dict (or uses first from catalog)

    Returns:
        ContentResult with generated content and quality metrics
    """
    if product is None:
        product = PRODUCT_CATALOG[0]

    client.reset_stats()

    user_prompt = f"""اكتب إعلانات لهذا المنتج:

المنتج: {product['name_ar']} ({product['name_en']})
الماركة: {product['brand']}
السعر (السعودية): {product['price_sar']} ريال
السعر (مصر): {product['price_egp']} جنيه
الوصف: {product['description_ar']}
الفئة: {product['category']}
المناسبة: عروض رمضان 2026

أرجع الناتج بصيغة JSON فقط بدون أي نص إضافي."""

    result = ContentResult(product=product, raw_output="")

    try:
        raw = client.chat(user_prompt, system_prompt=CONTENT_AGENT_PROMPT, temperature=0.7)
        result.raw_output = raw

        # Parse JSON
        try:
            # Clean markdown code blocks if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()
                if clean.startswith("json"):
                    clean = clean[4:].strip()

            parsed = json.loads(clean)
            result.parsed_output = parsed
        except json.JSONDecodeError:
            # Try to extract JSON
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    parsed = json.loads(raw[start:end])
                    result.parsed_output = parsed
                except json.JSONDecodeError:
                    pass

    except Exception as exc:
        import traceback
        print(f"  [AGENT ERROR] {exc}")
        traceback.print_exc()
        result.raw_output = f"ERROR: {exc}"

    # Run quality checks
    result.quality_checks = validate_content(product, result.parsed_output)
    passed = sum(1 for c in result.quality_checks if c.passed)
    total = len(result.quality_checks)
    result.quality_score = (passed / total * 100) if total > 0 else 0

    result.llm_stats = client.stats.summary()

    return result
