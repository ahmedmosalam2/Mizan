import re
import json
from typing import Any, Dict, List
from benchmarks.models import (
    CampaignPlanOutput,
    AdCopyOutput,
    PIIReport,
    BudgetDecision,
    DeploymentReport,
)




_PII_PATTERNS = {
    "saudi_national_id":    re.compile(r"\b[12]\d{9}\b"),
    "iqama_number":         re.compile(r"\b2\d{9}\b"),
    "egyptian_national_id": re.compile(r"\b[23]\d{13}\b"),
    "phone_numbers":        re.compile(
        r"\b(?:\+966|00966|0)?5[0-9]{8}\b"
        r"|\b(?:\+20|0020|0)?1[0-2]\d{8}\b"
        r"|\+\d{10,13}\b"
    ),
    "email_addresses":      re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "iban":                 re.compile(r"\bSA\d{22}\b|\bEG\d{27}\b"),
}
