"""SQLite database setup and insert helpers for JobPulse."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobpulse.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_postings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,          -- which API this came from (remotive, remoteok, ...)
    source_id   TEXT NOT NULL,          -- the posting's id on that source
    title       TEXT,
    company     TEXT,
    location    TEXT,
    remote      INTEGER DEFAULT 0,      -- 1 if the source is a remote-jobs board
    description TEXT,
    url         TEXT,
    salary_text TEXT,
    posted_at   TEXT,                   -- when the company posted it (ISO date, if known)
    ingested_at TEXT NOT NULL,          -- when we pulled it
    raw_json    TEXT,                   -- full original API payload, never throw data away
    UNIQUE (source, source_id)          -- same posting pulled twice = ignored, no duplicates
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def insert_postings(conn: sqlite3.Connection, source: str, postings: list[dict]) -> int:
    """Insert postings, skipping ones we already have. Returns how many were new."""
    now = datetime.now(timezone.utc).isoformat()
    new = 0
    for p in postings:
        cur = conn.execute(
            """INSERT OR IGNORE INTO raw_postings
               (source, source_id, title, company, location, remote, description,
                url, salary_text, posted_at, ingested_at, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source,
                str(p["source_id"]),
                p.get("title"),
                p.get("company"),
                p.get("location"),
                int(p.get("remote", 0)),
                p.get("description"),
                p.get("url"),
                p.get("salary_text"),
                p.get("posted_at"),
                now,
                json.dumps(p.get("raw", {}), ensure_ascii=False),
            ),
        )
        new += cur.rowcount
    conn.commit()
    return new
