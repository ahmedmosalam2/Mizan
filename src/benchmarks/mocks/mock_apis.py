"""
Mock API Clients — Simulate MENA e-commerce platform APIs
for deterministic benchmark testing.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime


class MockSallaAPI:
    """Mock Salla Partners API (Saudi e-commerce platform)."""

    def get_order(self, order_id: str) -> Dict:
        return {
            "id": order_id,
            "status": "shipped",
            "customer_name": "[REDACTED]",
            "total": {"amount": 899, "currency": "SAR"},
            "items": [{"sku": "KIT-001", "name_ar": "قلاية فيلبس الهوائية XXL", "qty": 1}],
            "shipping": {"carrier": "Aramex", "tracking": "ARX-12345678"},
            "created_at": "2026-02-28T14:30:00Z",
        }

    def search_products(self, query: str, limit: int = 5) -> List[Dict]:
        catalog = [
            {"sku": "KIT-001", "name_ar": "قلاية فيلبس الهوائية XXL", "price": 899, "stock": 45},
            {"sku": "ELEC-042", "name_ar": "سامسونج جالكسي تاب S9", "price": 2799, "stock": 12},
            {"sku": "GIFT-015", "name_ar": "طقم هدايا العود الفاخر", "price": 450, "stock": 120},
        ]
        return [p for p in catalog if query.lower() in p["name_ar"] or query.lower() in p["sku"].lower()][:limit]


class MockMetaAdsAPI:
    """Mock Meta Marketing API."""

    def create_campaign(self, name: str, budget: float, targeting: Dict) -> Dict:
        return {
            "id": f"meta_camp_{int(time.time())}",
            "name": name,
            "status": "ACTIVE",
            "budget": budget,
            "targeting": targeting,
            "created_at": datetime.now().isoformat(),
        }

    def get_insights(self, campaign_id: str) -> Dict:
        return {
            "campaign_id": campaign_id,
            "impressions": 45200,
            "clicks": 1830,
            "ctr": 4.05,
            "spend": 8500,
            "conversions": 127,
            "roas": 8.2,
            "cpa": 66.93,
        }

    def submit_whatsapp_template(self, template: Dict) -> Dict:
        # Simulate rejection for benchmark testing
        if template.get("force_reject"):
            return {"status": "REJECTED", "reason": "Template contains promotional content outside approved category"}
        return {"status": "APPROVED", "template_id": f"tpl_{int(time.time())}"}


class MockUnifonicAPI:
    """Mock Unifonic API (Saudi WhatsApp + SMS gateway)."""

    def send_whatsapp(self, to: str, template_id: str, params: List[str]) -> Dict:
        return {
            "message_id": f"wa_{int(time.time())}",
            "status": "sent",
            "to": to,
            "channel": "whatsapp",
        }

    def send_sms(self, to: str, body: str) -> Dict:
        return {
            "message_id": f"sms_{int(time.time())}",
            "status": "sent",
            "to": to,
            "channel": "sms",
            "body_length": len(body),
        }


class MockTamaraAPI:
    """Mock Tamara BNPL API (Saudi)."""

    def check_eligibility(self, customer_id: str, amount: float) -> Dict:
        return {
            "eligible": amount <= 5000,
            "customer_id": customer_id,
            "max_amount": 5000,
            "installments": [3, 6] if amount <= 5000 else [],
            "currency": "SAR",
        }

    def create_order(self, customer_id: str, amount: float, installments: int) -> Dict:
        return {
            "order_id": f"tamara_{int(time.time())}",
            "status": "approved",
            "installment_amount": round(amount / installments, 2),
            "next_payment_date": "2026-03-28",
        }


class MockFawryAPI:
    """Mock Fawry/FawryPay API (Egypt)."""

    def create_payment(self, amount: float, customer_phone: str) -> Dict:
        return {
            "reference_number": f"FWR{int(time.time())}",
            "status": "CREATED",
            "amount": amount,
            "currency": "EGP",
            "expiry": "2026-03-01T23:59:59Z",
        }

    def check_status(self, reference: str) -> Dict:
        return {
            "reference_number": reference,
            "status": "PAID",
            "paid_at": datetime.now().isoformat(),
        }


class MockAPIHub:
    """Central access point for all mock APIs."""

    def __init__(self):
        self.salla = MockSallaAPI()
        self.meta_ads = MockMetaAdsAPI()
        self.unifonic = MockUnifonicAPI()
        self.tamara = MockTamaraAPI()
        self.fawry = MockFawryAPI()

    def get_api(self, name: str):
        apis = {
            "salla": self.salla,
            "meta_ads": self.meta_ads,
            "meta": self.meta_ads,
            "unifonic": self.unifonic,
            "whatsapp": self.unifonic,
            "sms": self.unifonic,
            "tamara": self.tamara,
            "fawry": self.fawry,
        }
        return apis.get(name.lower())
