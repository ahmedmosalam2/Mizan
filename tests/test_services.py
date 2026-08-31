"""Tests for Mizan real services (Database, VectorStore, PIIEngine, CodeExecutor)."""

import pytest
from mizan.services.database import DatabaseService
from mizan.services.vector_store import VectorStore
from mizan.services.pii_engine import PIIEngine
from mizan.services.code_executor import CodeExecutor


@pytest.mark.asyncio
async def test_code_executor():
    code = "a = 10\nb = 20\nprint(a + b)"
    res = await CodeExecutor.execute_python(code)
    assert res["success"] is True
    assert "30" in res["stdout"].strip()


def test_pii_engine_saudi_and_egypt():
    text = "العميل في السعودية 1098765432 وجوال 0551234567، والعميل في مصر 29508150102345 وهاتف 01012345678"
    detections = PIIEngine.scan(text)
    assert "1098765432" in detections["saudi_national_id"]
    assert "29508150102345" in detections["egyptian_national_id"]
    assert len(detections["phone"]) >= 2

    redacted, audit = PIIEngine.redact(text, jurisdiction="KSA")
    assert "[REDACTED_SAUDI_ID]" in redacted
    assert "[REDACTED_EGYPT_ID]" in redacted
    assert "1098765432" not in redacted
    assert audit["total_redactions"] >= 4


def test_vector_store():
    products = [
        {"sku": "SKU-1", "name_en": "Philips Air Fryer XXL", "name_ar": "قلاية فيليبس", "category": "kitchen"},
        {"sku": "SKU-2", "name_en": "Samsung QLED Smart TV", "name_ar": "تلفزيون سامسونج", "category": "tv"},
    ]
    vstore = VectorStore()
    vstore.index_products(products)
    res = vstore.search("قلاية هوائية فيليبس", top_k=1)
    assert len(res) == 1
    assert res[0]["sku"] == "SKU-1"


def test_database_service(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = DatabaseService(db_file)
    db.seed_products([{"sku": "SKU-1", "name_en": "TV", "name_ar": "تلفزيون", "category": "electronics"}])
    found = db.query_products("تلفزيون")
    assert len(found) == 1
    assert found[0]["sku"] == "SKU-1"

    db.save_memory("CUST-1", "pref_color", "white")
    mem = db.get_all_memory("CUST-1")
    assert mem.get("pref_color") == "white"
