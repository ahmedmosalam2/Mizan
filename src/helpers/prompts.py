"""
Prompt Builders — كل الـ task prompts في مكان واحد
كل function بتاخد الـ data وبترجع الـ prompt string جاهز للـ agent
"""

import json
from typing import Dict, List

from benchmarks.adapters.crewai.config import (
    BUDGET_REALLOCATION_THRESHOLD as _DEFAULT_THRESHOLD,
)
from benchmarks.scenarios.test_data import (
    BUDGET_REALLOCATION_REQUEST,
)

# Derived constants from test_data
_ROAS_THRESHOLD       = 2.0
_SNAPCHAT_ROAS        = BUDGET_REALLOCATION_REQUEST["current_allocation"]["snapchat"]["roas"]
_META_ROAS            = BUDGET_REALLOCATION_REQUEST["current_allocation"]["meta_ads"]["roas"]
_SNAPCHAT_REALLOC_SAR = BUDGET_REALLOCATION_REQUEST["recommendation"]["amount_sar"]
BUDGET_REALLOCATION_THRESHOLD = _DEFAULT_THRESHOLD


def build_orchestration_prompt(task: Dict) -> str:
    brief_str = json.dumps(task, ensure_ascii=False, indent=2)
    return (
        f"أنت Campaign Commander لـ RetailCo. قُد الفريق لتنفيذ الحملة.\n\n"
        f"Brief:\n{brief_str}\n\n"
        f"المطلوب:\n"
        f"1. حدد deliverable لكل agent بوضوح\n"
        f"2. اعمل channel plan بالميزانية والـ content type\n"
        f"3. حدد KPIs لكل market\n"
        f"4. اعمل compliance checklist للـ PDPL وقانون 151"
    )


def build_content_generation_prompt(task: Dict) -> str:
    product = task.get("product", {})
    return (
        f"المهمة: {task.get('goal', 'Generate ad copy')}\n\n"
        f"المنتج: {product.get('name_ar', '')} (SKU: {product.get('sku', '')})\n"
        f"السوق: {task.get('market', 'KSA')}\n"
        f"الجمهور: {task.get('audience', '')}\n"
        f"الـ tone: {task.get('tone', 'دافئ ورمضاني')}\n"
        f"القيود: {json.dumps(task.get('constraints', []), ensure_ascii=False)}\n\n"
        f"اكتب:\n"
        f"1. Gulf Arabic carousel variant\n"
        f"2. Gulf Arabic single image variant\n"
        f"3. English carousel variant\n"
        f"4. WhatsApp template (Meta-compliant)\n"
        f"تأكد من ذكر السعر بالريال السعودي."
    )


def build_deploy_channels_prompt(channels: List[Dict]) -> str:
    channels_str = json.dumps(channels, ensure_ascii=False, indent=2)
    return (
        f"انشر الحملة على هذه الـ channels:\n{channels_str}\n\n"
        f"استخدم deploy_channel لكل channel (JSON input).\n"
        f"- API_RATE_LIMIT → retry حتى 3 مرات قبل التخلي\n"
        f"- TEMPLATE_REJECTED → اعمل fallback لـ SMS\n\n"
        f"أنتج deployment report كامل."
    )


def build_analytics_prompt(
    task: Dict,
    threshold: float = BUDGET_REALLOCATION_THRESHOLD,
) -> str:
    realloc_pct = task.get("recommendation", {}).get("percentage_of_channel_budget", 50) / 100
    needs_approval = realloc_pct > threshold
    return (
        f"حلّل أداء الحملة:\n{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
        f"الـ threshold للموافقة: {threshold * 100:.0f}%\n"
        f"التغيير المقترح: {realloc_pct * 100:.0f}% "
        f"({'يحتاج موافقة ✋' if needs_approval else 'لا يحتاج موافقة ✅'})\n\n"
        f"قدّم توصية واضحة مع مبررات ROAS."
    )


def build_approval_prompt(threshold: float = BUDGET_REALLOCATION_THRESHOLD) -> str:
    return (
        f"التوصية تعدّت الـ {threshold * 100:.0f}% threshold.\n"
        f"اعرض التوصية على المدير وانتظر قراره.\n"
        f"طبّق الـ feedback على الخطة النهائية."
    )


def build_memory_session1_prompt(session: Dict) -> str:
    history_text = "\n".join(
        f"{'العميل' if m['role'] == 'customer' else 'الوكيل'}: {m['content']}"
        for m in session.get("messages", [])
    )
    return (
        f"المحادثة مع العميل {session.get('customer_id', 'CUST-101')}:\n\n"
        f"{history_text}\n\n"
        f"لخّص المحادثة واحفظ: المنتج + السعر بعد الخصم + اللون + الفرع."
    )


def build_memory_session2_prompt(follow_up: str) -> str:
    return (
        f"عميل عاد للتواصل:\n'{follow_up}'\n\n"
        f"رد عليه بتذكّر تفاصيل محادثته السابقة.\n"
        f"لا تسأله عن معلومات موجودة في سجله."
    )


def build_pii_scan_prompt(
    redacted_text: str,
    original_text: str,
    jurisdiction: str,
    jurisdiction_rules: str,
) -> str:
    return (
        f"النص بعد الـ regex redaction:\n{redacted_text}\n\n"
        f"النص الأصلي للمقارنة:\n{original_text}\n\n"
        f"Jurisdiction: {jurisdiction}\n"
        f"القواعد: {jurisdiction_rules}\n\n"
        f"ابحث عن PII إضافية:\n"
        f"- أسماء أشخاص\n- عناوين\n- معلومات مالية ضمنية\n\n"
        f"الـ risk level: critical لو National ID موجود، "
        f"high لو phone/email، medium لو اسم فقط."
    )


def build_multimodal_prompt(
    task: Dict,
    is_vision: bool,
    image_path: str = None,
) -> str:
    product = task.get("product", {})
    vision_note = (
        "⚠️ Vision model active — analyze the product image directly."
        if is_vision
        else "⚠️ Text-only model — use get_product_details tool for specs."
    )
    requirements = "\n".join(f"- {r}" for r in task.get("requirements", []))
    image_line = f"Image: {image_path}" if image_path and is_vision else ""
    return (
        f"{vision_note}\n\n"
        f"المنتج: {product.get('name_ar', '')} | SKU: {product.get('sku', '')}\n"
        f"{image_line}\n"
        f"السوق: {task.get('market', 'KSA')}\n"
        f"الفورمات: {task.get('format', 'meta_carousel')}\n\n"
        f"المتطلبات:\n{requirements}\n\n"
        f"اكتب:\n"
        f"1. Headline (max 40 حرف)\n"
        f"2. Description (max 125 حرف)\n"
        f"3. Call-to-Action\n"
        f"4. Body copy للـ carousel\n"
        f"باللغة العربية الخليجية. راعِ حساسية رمضان."
    )


def build_flow_deploy_prompt(content: str) -> str:
    return (
        f"انشر هذا الـ content:\n{content}\n\n"
        f"على الـ channels: Meta Ads (KSA+EG), Snapchat (KSA), "
        f"Google Ads (KSA), WhatsApp (KSA), Email (EG)\n\n"
        f"تعليمات الأخطاء:\n"
        f"- Snapchat API_RATE_LIMIT → retry حتى 3 مرات\n"
        f"- WhatsApp TEMPLATE_REJECTED → fallback SMS"
    )


def build_flow_analytics_prompt(deployment_result: str) -> str:
    return (
        f"بعد الـ deployment:\n{deployment_result}\n\n"
        f"حلّل الأداء الأولي وهل تحتاج إعادة توزيع ميزانية؟\n"
        f"Snapchat ROAS = {_SNAPCHAT_ROAS}x (أقل من threshold {_ROAS_THRESHOLD}x)\n"
        f"Meta ROAS = {_META_ROAS}x (الأعلى)\n"
        f"التوصية: نقل {_SNAPCHAT_REALLOC_SAR:,} SAR من Snapchat لـ Meta "
        f"(50% من ميزانية Snapchat)"
    )
