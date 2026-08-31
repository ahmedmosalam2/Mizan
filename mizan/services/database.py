"""
Real SQLite Database Service for Mizan.

Initializes and manages the production-grade schema for the Ramadan campaign:
- products (5,000+ SKUs or catalog items)
- customers (KSA/EG with consent status and locale)
- orders & BNPL records (Tamara, Tabby, Fawry)
- campaigns & channel deployments
- consent_audit_log (PDPL compliance records)
- approval_gates (HITL persistent state)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseService:
    """Manages SQLite database operations for the benchmark scenario."""

    def __init__(self, db_path: str = "mizan_ramadan.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    sku TEXT PRIMARY KEY,
                    name_en TEXT NOT NULL,
                    name_ar TEXT NOT NULL,
                    category TEXT NOT NULL,
                    regular_price_sar REAL,
                    ramadan_price_sar REAL,
                    regular_price_egp REAL,
                    ramadan_price_egp REAL,
                    discount_percent INTEGER,
                    colors TEXT, -- JSON array
                    branches_ksa TEXT, -- JSON array
                    branches_eg TEXT, -- JSON array
                    description_en TEXT,
                    description_ar TEXT
                );

                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    national_id TEXT,
                    phone TEXT,
                    email TEXT,
                    market TEXT NOT NULL, -- 'KSA' or 'EG'
                    consent_status TEXT NOT NULL, -- 'opted_in', 'opted_out', 'unsubscribed'
                    consent_date TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    market TEXT NOT NULL,
                    budget_allocated REAL,
                    budget_spent REAL DEFAULT 0,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS channel_deployments (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT,
                    channel TEXT NOT NULL, -- 'meta_ads', 'google_ads', 'snapchat', 'whatsapp', 'sms'
                    market TEXT NOT NULL,
                    content TEXT,
                    status TEXT NOT NULL, -- 'pending', 'active', 'failed', 'retried'
                    error_reason TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS consent_audit_log (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    action TEXT NOT NULL, -- 'send_marketing', 'blocked_no_consent', 'consent_checked'
                    channel TEXT,
                    jurisdiction TEXT NOT NULL, -- 'KSA_PDPL' or 'EG_LAW_151'
                    timestamp TEXT NOT NULL,
                    details TEXT
                );

                CREATE TABLE IF NOT EXISTS approval_gates (
                    gate_id TEXT PRIMARY KEY,
                    gate_type TEXT NOT NULL,
                    action_description TEXT NOT NULL,
                    amount REAL,
                    shift_ratio REAL,
                    required_role TEXT NOT NULL,
                    status TEXT NOT NULL, -- 'pending', 'approved', 'rejected', 'auto_approved'
                    context TEXT, -- JSON
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    resolved_by TEXT
                );

                CREATE TABLE IF NOT EXISTS customer_memory (
                    customer_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (customer_id, key)
                );
            """)
            conn.commit()

    def seed_products(self, products: List[Dict[str, Any]]) -> None:
        """Seed products catalog into SQLite database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for p in products:
                cursor.execute("""
                    INSERT OR REPLACE INTO products (
                        sku, name_en, name_ar, category,
                        regular_price_sar, ramadan_price_sar,
                        regular_price_egp, ramadan_price_egp,
                        discount_percent, colors, branches_ksa, branches_eg,
                        description_en, description_ar
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["sku"],
                    p["name_en"],
                    p["name_ar"],
                    p["category"],
                    p.get("regular_price_sar"),
                    p.get("ramadan_price_sar"),
                    p.get("regular_price_egp"),
                    p.get("ramadan_price_egp"),
                    p.get("discount_percent", 0),
                    json.dumps(p.get("colors", [])),
                    json.dumps(p.get("branches_available_ksa", [])),
                    json.dumps(p.get("branches_available_eg", [])),
                    p.get("description_en", ""),
                    p.get("description_ar", ""),
                ))
            conn.commit()

    def seed_customers(self, customers: List[Dict[str, Any]]) -> None:
        """Seed customer records into SQLite database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for c in customers:
                cursor.execute("""
                    INSERT OR REPLACE INTO customers (
                        id, name, national_id, phone, email, market, consent_status, consent_date, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    c["id"],
                    c["name"],
                    c.get("national_id"),
                    c.get("phone"),
                    c.get("email"),
                    c.get("market", "KSA"),
                    c.get("consent_status", "opted_in"),
                    c.get("consent_date", "2026-01-01"),
                    c.get("created_at", "2026-01-01"),
                ))
            conn.commit()

    def query_products(self, search_term: str, category: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Query product catalog with SQL keyword matching."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{search_term}%"
            if category:
                cursor.execute("""
                    SELECT * FROM products
                    WHERE category = ? AND (name_en LIKE ? OR name_ar LIKE ? OR description_en LIKE ? OR description_ar LIKE ?)
                    LIMIT ?
                """, (category, pattern, pattern, pattern, pattern, limit))
            else:
                cursor.execute("""
                    SELECT * FROM products
                    WHERE name_en LIKE ? OR name_ar LIKE ? OR description_en LIKE ? OR description_ar LIKE ?
                    LIMIT ?
                """, (pattern, pattern, pattern, pattern, limit))

            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve customer details by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def log_consent_action(self, customer_id: str, action: str, channel: str, jurisdiction: str, details: str = "") -> None:
        """Insert immutable audit log entry for regulatory compliance."""
        import uuid
        from datetime import datetime
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO consent_audit_log (id, customer_id, action, channel, jurisdiction, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), customer_id, action, channel, jurisdiction, datetime.now().isoformat(), details
            ))
            conn.commit()

    def save_memory(self, customer_id: str, key: str, value: str) -> None:
        """Save a memory key/value for a customer."""
        from datetime import datetime
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO customer_memory (customer_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
            """, (customer_id, key, value, datetime.now().isoformat()))
            conn.commit()

    def get_all_memory(self, customer_id: str) -> Dict[str, str]:
        """Fetch all stored memories for a customer."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM customer_memory WHERE customer_id = ?", (customer_id,))
            rows = cursor.fetchall()
            return {r["key"]: r["value"] for r in rows}
