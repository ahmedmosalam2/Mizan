from typing import Any, Dict, List
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════
# Pydantic Models for Structured Output
# ═══════════════════════════════════════════════════════════════════════

class CampaignPlanOutput(BaseModel):
    campaign_name: str = Field(description="اسم الحملة")
    agent_assignments: Dict[str, str] = Field(
        description="مين مسؤول عن إيه: {agent_name: deliverable}"
    )
    channel_plan: Dict[str, Any] = Field(
        description="خطة كل channel: {channel: {budget, content_type, market}}"
    )
    content_requirements: List[str] = Field(
        description="المتطلبات الـ content"
    )
    kpis: Dict[str, str] = Field(
        description="KPIs لكل market: {market: kpi_description}"
    )
    compliance_checklist: List[str] = Field(
        description="PDPL + Law 151 compliance items"
    )


class AdCopyOutput(BaseModel):
    variant_gulf_arabic_carousel: str = Field(description="Gulf Arabic — carousel format")
    variant_gulf_arabic_single: str   = Field(description="Gulf Arabic — single image")
    variant_english_carousel: str     = Field(description="English — carousel format")
    whatsapp_template: str            = Field(description="WhatsApp template (Meta compliant)")
    product_sku: str                  = Field(description="SKU المنتج المستخدم")
    price_mentioned_sar: bool         = Field(description="هل ذكر السعر بالريال؟")


class PIIReport(BaseModel):
    detected_pii: Dict[str, List[str]] = Field(description="PII types → values found")
    redacted_text: str                 = Field(description="النص بعد الـ redaction")
    compliance_notes: str              = Field(description="ملاحظات الـ compliance")
    risk_level: str                    = Field(description="low | medium | high | critical")
    jurisdiction_applied: str          = Field(description="KSA | EG | both")


class BudgetDecision(BaseModel):
    original_allocation: Dict[str, float] = Field(description="الميزانية الأصلية")
    recommended_changes: Dict[str, float] = Field(description="التغييرات المقترحة")
    human_decision: str                   = Field(description="approved | rejected | modified")
    human_feedback: str                   = Field(description="تعليق المدير")
    final_allocation: Dict[str, float]    = Field(description="الميزانية النهائية")
    requires_approval: bool               = Field(description="هل تعدّت الـ threshold؟")


class DeploymentReport(BaseModel):
    channel_results: List[Dict[str, Any]] = Field(description="نتيجة كل channel")
    total_deployed: int                   = Field(description="عدد channels نجحت")
    total_failed: int                     = Field(description="عدد channels فشلت")
    fallbacks_used: List[str]             = Field(description="الـ fallback channels المستخدمة")
    retry_attempts: Dict[str, int]        = Field(description="عدد retries لكل channel")
