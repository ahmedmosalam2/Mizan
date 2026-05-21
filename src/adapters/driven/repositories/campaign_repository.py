import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class CampaignRepository:
    """Persist campaign data to SQLite database."""

    def __init__(self, db_path: str = "campaigns.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brief JSON NOT NULL,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                market TEXT,
                budget REAL,
                currency TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_executions (
                id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT,
                result JSON,
                execution_time_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )
        """)

        conn.commit()
        conn.close()

    def save_campaign(
        self,
        campaign_id: str,
        name: str,
        brief: Dict[str, Any],
        status: str = "active"
    ) -> bool:
        """Save campaign to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO campaigns 
                (id, name, brief, status, updated_at, market, budget, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign_id,
                name,
                json.dumps(brief, ensure_ascii=False),
                status,
                datetime.now().isoformat(),
                brief.get("market"),
                brief.get("total_budget"),
                brief.get("currency")
            ))
            conn.commit()
            return True
        finally:
            conn.close()

    def save_agent_execution(
        self,
        execution_id: str,
        campaign_id: str,
        agent_name: str,
        status: str,
        result: Dict[str, Any],
        execution_time_ms: float
    ) -> bool:
        """Save agent execution result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO agent_executions
                (id, campaign_id, agent_name, status, result, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                campaign_id,
                agent_name,
                status,
                json.dumps(result, ensure_ascii=False),
                execution_time_ms
            ))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve campaign by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def get_agent_executions(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Retrieve all agent executions for a campaign."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM agent_executions WHERE campaign_id = ? ORDER BY created_at DESC",
                (campaign_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def list_campaigns(self) -> List[Dict[str, Any]]:
        """List all campaigns."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id, name, status, created_at, market, budget FROM campaigns ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()