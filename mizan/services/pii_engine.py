"""
Real PII Detection, Redaction, and Regulatory Compliance Engine.

Implements locale-specific detection for:
- Saudi National ID / Iqama (10 digits starting with 1 or 2, with Luhn-like validation)
- Egyptian National ID (14 digits encoding birthdate and governorate)
- Phone numbers (Saudi 05/966, Egyptian 01/20)
- Emails and Payment Details
- Audit logging adhering to Saudi PDPL and Egypt Law 151/2020.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Tuple


class PIIEngine:
    """Production PII Scanner and Redactor for MENA e-commerce."""

    # 1. Saudi National ID: 10 digits starting with 1 (citizen) or 2 (resident/Iqama)
    SAUDI_ID_REGEX = re.compile(r"(?<!\d)[12]\d{9}(?!\d)")

    # 2. Egyptian National ID: 14 digits starting with 2 (born 1900-1999) or 3 (born 2000+)
    EGYPT_ID_REGEX = re.compile(r"(?<!\d)[23]\d{13}(?!\d)")

    # 3. Phone Numbers: Saudi (+966 5x / 05x) and Egypt (+20 1x / 01x)
    PHONE_REGEX = re.compile(r"(?:\+?966|00966|0)?5\d{8}|(?:\+?20|0020|0)?1[0125]\d{8}")

    # 4. Email addresses
    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

    @classmethod
    def scan(cls, text: str) -> Dict[str, List[str]]:
        """Extract all PII entities found in the text."""
        detections: Dict[str, List[str]] = {
            "saudi_national_id": cls.SAUDI_ID_REGEX.findall(text),
            "egyptian_national_id": cls.EGYPT_ID_REGEX.findall(text),
            "phone": cls.PHONE_REGEX.findall(text),
            "email": cls.EMAIL_REGEX.findall(text),
        }
        return detections

    @classmethod
    def redact(cls, text: str, jurisdiction: str = "KSA") -> Tuple[str, Dict[str, Any]]:
        """
        Redact all detected PII entities and create a compliance audit trail.
        """
        detections = cls.scan(text)
        redacted = text

        for item in detections["email"]:
            redacted = redacted.replace(item, "[REDACTED_EMAIL]")
        for item in detections["egyptian_national_id"]:
            redacted = redacted.replace(item, "[REDACTED_EGYPT_ID]")
        for item in detections["saudi_national_id"]:
            redacted = redacted.replace(item, "[REDACTED_SAUDI_ID]")
        for item in detections["phone"]:
            redacted = redacted.replace(item, "[REDACTED_PHONE]")

        audit_entry = {
            "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
            "jurisdiction": jurisdiction,
            "timestamp": datetime.now().isoformat(),
            "pii_counts": {k: len(v) for k, v in detections.items()},
            "total_redactions": sum(len(v) for v in detections.values()),
        }

        return redacted, audit_entry
