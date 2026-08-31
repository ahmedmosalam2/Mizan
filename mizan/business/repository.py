"""Tenant-scoped SQLite repository for the executable local Sandbox AUT.

This repository is intentionally limited to `SANDBOX` execution. PostgreSQL
will replace it for production, but it provides a real persisted workflow for
development without presenting fixture behavior as a production deployment.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from mizan.core.contracts import ApprovalStatus, CampaignStateMachine, CampaignStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SandboxRepository:
    """Persistence boundary that requires `company_id` for every business read."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    company_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    sku TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    name_ar TEXT NOT NULL,
                    category TEXT NOT NULL,
                    ramadan_price_sar REAL,
                    ramadan_price_egp REAL,
                    description_en TEXT NOT NULL DEFAULT '',
                    description_ar TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (company_id, sku)
                );

                CREATE TABLE IF NOT EXISTS customers (
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    customer_id TEXT NOT NULL,
                    market TEXT NOT NULL CHECK (market IN ('KSA', 'EG')),
                    consent_status TEXT NOT NULL CHECK (consent_status IN ('opted_in', 'opted_out', 'unsubscribed')),
                    PRIMARY KEY (company_id, customer_id)
                );

                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    name TEXT NOT NULL,
                    market TEXT NOT NULL CHECK (market IN ('KSA', 'EG')),
                    budget REAL NOT NULL CHECK (budget >= 0),
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS campaign_tasks (
                    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (campaign_id, task_id)
                );

                CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS tool_calls (
                    tool_call_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES agent_runs(run_id),
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    duration_ms REAL NOT NULL,
                    error_code TEXT,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS approval_gates (
                    approval_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
                    task_id TEXT NOT NULL,
                    requested_action TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    required_role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    approved_by TEXT,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                );

                CREATE TABLE IF NOT EXISTS consent_audit_log (
                    audit_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
                    customer_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );

                CREATE TRIGGER IF NOT EXISTS consent_audit_log_no_update
                BEFORE UPDATE ON consent_audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'consent audit records are immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS consent_audit_log_no_delete
                BEFORE DELETE ON consent_audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'consent audit records are immutable');
                END;

                CREATE TABLE IF NOT EXISTS channel_deployments (
                    deployment_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
                    channel TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    fallback_from TEXT,
                    error_code TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS campaign_metrics (
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    PRIMARY KEY (campaign_id, metric_name)
                );

                CREATE TABLE IF NOT EXISTS customer_memory (
                    company_id TEXT NOT NULL REFERENCES companies(company_id),
                    customer_id TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (company_id, customer_id, memory_key)
                );

                CREATE INDEX IF NOT EXISTS idx_campaign_company ON campaigns(company_id);
                CREATE INDEX IF NOT EXISTS idx_customer_company ON customers(company_id, customer_id);
                CREATE INDEX IF NOT EXISTS idx_tool_calls_campaign ON tool_calls(company_id, campaign_id);
                CREATE INDEX IF NOT EXISTS idx_audit_campaign ON consent_audit_log(company_id, campaign_id);
                """
            )

    def ensure_company(self, company_id: str, name: str = "Sandbox Retail Company") -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO companies (company_id, name, created_at) VALUES (?, ?, ?)",
                (company_id, name, utc_now()),
            )

    def seed_catalog(self, company_id: str, products: list[dict[str, Any]]) -> None:
        with self._connection() as connection:
            for product in products:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO products (
                        company_id, sku, name_en, name_ar, category, ramadan_price_sar,
                        ramadan_price_egp, description_en, description_ar
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        company_id,
                        product["sku"],
                        product["name_en"],
                        product["name_ar"],
                        product["category"],
                        product.get("ramadan_price_sar"),
                        product.get("ramadan_price_egp"),
                        product.get("description_en", ""),
                        product.get("description_ar", ""),
                    ),
                )

    def seed_customers(self, company_id: str, customers: list[dict[str, Any]]) -> None:
        with self._connection() as connection:
            for customer in customers:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO customers (company_id, customer_id, market, consent_status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (company_id, customer["id"], customer["market"], customer["consent_status"]),
                )

    def create_campaign(self, campaign_id: str, company_id: str, name: str, market: str, budget: float) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO campaigns (
                    campaign_id, company_id, name, market, budget, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (campaign_id, company_id, name, market, budget, CampaignStatus.DRAFT.value, now, now),
            )

    def get_campaign(self, company_id: str, campaign_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM campaigns WHERE company_id = ? AND campaign_id = ?", (company_id, campaign_id)
            ).fetchone()
        if row is None:
            raise LookupError("Campaign was not found in the requested company")
        return dict(row)

    def transition_campaign(
        self, company_id: str, campaign_id: str, target: CampaignStatus
    ) -> CampaignStatus:
        campaign = self.get_campaign(company_id, campaign_id)
        current = CampaignStatus(campaign["status"])
        CampaignStateMachine.require_transition(current, target)
        with self._connection() as connection:
            updated = connection.execute(
                """
                UPDATE campaigns SET status = ?, updated_at = ?
                WHERE company_id = ? AND campaign_id = ? AND status = ?
                """,
                (target.value, utc_now(), company_id, campaign_id, current.value),
            ).rowcount
        if updated != 1:
            raise RuntimeError("Campaign transition lost its concurrency check")
        return target

    def create_task(self, company_id: str, campaign_id: str, task_id: str, agent_id: str, payload: dict[str, Any]) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO campaign_tasks (
                    campaign_id, company_id, task_id, agent_id, status, payload_json, created_at
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (campaign_id, company_id, task_id, agent_id, json.dumps(payload), utc_now()),
            )

    def start_agent_run(self, company_id: str, campaign_id: str, task_id: str, agent_id: str) -> str:
        run_id = str(uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs (run_id, campaign_id, company_id, task_id, agent_id, status, started_at)
                VALUES (?, ?, ?, ?, ?, 'running', ?)
                """,
                (run_id, campaign_id, company_id, task_id, agent_id, utc_now()),
            )
        return run_id

    def finish_agent_run(self, run_id: str, status: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE agent_runs SET status = ?, finished_at = ? WHERE run_id = ?",
                (status, utc_now(), run_id),
            )

    def record_tool_call(
        self,
        *,
        run_id: str,
        company_id: str,
        campaign_id: str,
        task_id: str,
        agent_id: str,
        tool_name: str,
        success: bool,
        duration_ms: float,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
        error_code: str | None = None,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO tool_calls (
                    tool_call_id, run_id, company_id, campaign_id, task_id, agent_id, tool_name,
                    success, duration_ms, error_code, input_json, output_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()), run_id, company_id, campaign_id, task_id, agent_id, tool_name,
                    int(success), duration_ms, error_code, json.dumps(input_payload),
                    json.dumps(output_payload), utc_now(),
                ),
            )

    def list_products(self, company_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM products WHERE company_id = ? ORDER BY sku", (company_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_customer_consent(self, company_id: str, customer_id: str) -> tuple[str, str]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT market, consent_status FROM customers
                WHERE company_id = ? AND customer_id = ?
                """,
                (company_id, customer_id),
            ).fetchone()
        if row is None:
            raise LookupError("Customer was not found in the requested company")
        return row["market"], row["consent_status"]

    def append_consent_audit(
        self, company_id: str, campaign_id: str, customer_id: str, action: str, jurisdiction: str, details: dict[str, Any]
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO consent_audit_log (
                    audit_id, company_id, campaign_id, customer_id, action, jurisdiction, created_at, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), company_id, campaign_id, customer_id, action, jurisdiction, utc_now(), json.dumps(details)),
            )

    def create_approval(
        self,
        company_id: str,
        campaign_id: str,
        task_id: str,
        requested_action: str,
        risk: str,
        required_role: str,
        requested_by: str,
        reason: str,
    ) -> str:
        approval_id = str(uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO approval_gates (
                    approval_id, company_id, campaign_id, task_id, requested_action, risk,
                    required_role, status, requested_by, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (approval_id, company_id, campaign_id, task_id, requested_action, risk, required_role,
                 ApprovalStatus.PENDING.value, requested_by, reason, utc_now()),
            )
        return approval_id

    def get_approval(self, company_id: str, approval_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM approval_gates WHERE company_id = ? AND approval_id = ?", (company_id, approval_id)
            ).fetchone()
        if row is None:
            raise LookupError("Approval was not found in the requested company")
        return dict(row)

    def decide_approval(self, company_id: str, approval_id: str, approved_by: str, approved: bool) -> ApprovalStatus:
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        with self._connection() as connection:
            updated = connection.execute(
                """
                UPDATE approval_gates
                SET status = ?, approved_by = ?, decided_at = ?
                WHERE company_id = ? AND approval_id = ? AND status = ?
                """,
                (status.value, approved_by, utc_now(), company_id, approval_id, ApprovalStatus.PENDING.value),
            ).rowcount
        if updated != 1:
            raise RuntimeError("Approval is not pending or does not belong to the requested company")
        return status

    def record_deployment(
        self,
        company_id: str,
        campaign_id: str,
        channel: str,
        attempt: int,
        status: str,
        idempotency_key: str,
        fallback_from: str | None = None,
        error_code: str | None = None,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO channel_deployments (
                    deployment_id, company_id, campaign_id, channel, attempt, status,
                    fallback_from, error_code, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), company_id, campaign_id, channel, attempt, status, fallback_from, error_code,
                 idempotency_key, utc_now()),
            )

    def list_deployments(self, company_id: str, campaign_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT channel, attempt, status, fallback_from, error_code
                FROM channel_deployments WHERE company_id = ? AND campaign_id = ?
                ORDER BY created_at
                """,
                (company_id, campaign_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_metrics(self, company_id: str, campaign_id: str, metrics: dict[str, float]) -> None:
        with self._connection() as connection:
            for name, value in metrics.items():
                connection.execute(
                    """
                    INSERT OR REPLACE INTO campaign_metrics (company_id, campaign_id, metric_name, metric_value)
                    VALUES (?, ?, ?, ?)
                    """,
                    (company_id, campaign_id, name, value),
                )

    def get_metrics(self, company_id: str, campaign_id: str) -> dict[str, float]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT metric_name, metric_value FROM campaign_metrics
                WHERE company_id = ? AND campaign_id = ?
                """,
                (company_id, campaign_id),
            ).fetchall()
        return {row["metric_name"]: row["metric_value"] for row in rows}

    def save_customer_memory(self, company_id: str, customer_id: str, key: str, value: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO customer_memory (company_id, customer_id, memory_key, memory_value, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (company_id, customer_id, key, value, utc_now()),
            )

    def get_customer_memory(self, company_id: str, customer_id: str) -> dict[str, str]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT memory_key, memory_value FROM customer_memory
                WHERE company_id = ? AND customer_id = ?
                """,
                (company_id, customer_id),
            ).fetchall()
        return {row["memory_key"]: row["memory_value"] for row in rows}
