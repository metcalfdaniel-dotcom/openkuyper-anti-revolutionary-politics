"""OpenKuyper Notion Worker — SQLite checkpoint store"""
import sqlite3
from pathlib import Path
from datetime import datetime

from notion_worker_config import CHECKPOINT_DB_PATH


def _ensure_db():
    CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_sync_timestamp TEXT,
            pages_synced INTEGER DEFAULT 0,
            senses_synced INTEGER DEFAULT 0,
            drift_alerts_created INTEGER DEFAULT 0,
            git_commit_sha TEXT,
            run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS enriched_terms (
            term_page_id TEXT PRIMARY KEY,
            term TEXT,
            enriched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def get_last_checkpoint() -> str:
    """Return ISO 8601 timestamp of last successful sync, or epoch if none."""
    _ensure_db()
    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH))
    row = conn.execute(
        "SELECT last_sync_timestamp FROM checkpoints ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row[0] if row and row[0] else "1970-01-01T00:00:00Z"


def save_checkpoint(timestamp: str, pages: int = 0, senses: int = 0, drifts: int = 0, git_sha: str = ""):
    _ensure_db()
    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH))
    conn.execute(
        "INSERT INTO checkpoints (last_sync_timestamp, pages_synced, senses_synced, drift_alerts_created, git_commit_sha) VALUES (?, ?, ?, ?, ?)",
        (timestamp, pages, senses, drifts, git_sha),
    )
    conn.commit()
    conn.close()


def is_enriched(term_page_id: str) -> bool:
    _ensure_db()
    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH))
    row = conn.execute(
        "SELECT 1 FROM enriched_terms WHERE term_page_id = ?", (term_page_id,)
    ).fetchone()
    conn.close()
    return row is not None


def mark_enriched(term_page_id: str, term: str):
    _ensure_db()
    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH))
    conn.execute(
        "INSERT OR REPLACE INTO enriched_terms (term_page_id, term) VALUES (?, ?)",
        (term_page_id, term),
    )
    conn.commit()
    conn.close()
