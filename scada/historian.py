"""
SCADA Historian — time-series storage for all sensor readings.

Logs every poll cycle's readings to SQLite. Provides query APIs for
trend charts, daily reports, and data export.
"""

from __future__ import annotations

import sqlite3
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DEFAULT_DB_PATH = Path("/data/scada.db")


def _resolve_db_path() -> Path:
    """Return /data/scada.db if writable, otherwise fall back to a temp dir."""
    path = _DEFAULT_DB_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Quick write-permission probe
        probe = path.parent / ".write_probe"
        probe.touch()
        probe.unlink()
        return path
    except OSError:
        import tempfile
        fallback = Path(tempfile.gettempdir()) / "scada.db"
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Cannot write to %s — using fallback DB at %s", path, fallback
        )
        return fallback


DB_PATH: Path = _resolve_db_path()

_db_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            value REAL,
            timestamp REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_readings_tag_ts ON readings(tag, timestamp);

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            event_type TEXT NOT NULL,
            tag TEXT,
            message TEXT,
            value REAL
        );

        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);

        CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            date TEXT NOT NULL,
            min_value REAL,
            max_value REAL,
            avg_value REAL,
            sample_count INTEGER,
            UNIQUE(tag, date)
        );
    """)
    conn.commit()


# --- Readings ---

def log_reading(tag: str, value: Any, timestamp: float = None) -> None:
    """Log a single sensor reading."""
    if value is None:
        return
    if isinstance(value, bool):
        value = 1.0 if value else 0.0
    if not isinstance(value, (int, float)):
        return
    ts = timestamp or time.time()
    with _db_lock:
        get_db().execute(
            "INSERT INTO readings (tag, value, timestamp) VALUES (?, ?, ?)",
            (tag, float(value), ts),
        )
        get_db().commit()


def log_readings_batch(readings: List[Tuple[str, float, float]]) -> None:
    """Log multiple readings at once. Each tuple: (tag, value, timestamp)."""
    cleaned = []
    for tag, value, ts in readings:
        if value is None:
            continue
        if isinstance(value, bool):
            value = 1.0 if value else 0.0
        if not isinstance(value, (int, float)):
            continue
        cleaned.append((tag, float(value), ts))

    if not cleaned:
        return
    with _db_lock:
        get_db().executemany(
            "INSERT INTO readings (tag, value, timestamp) VALUES (?, ?, ?)",
            cleaned,
        )
        get_db().commit()


def get_trend_data(tag: str, duration_s: float = 3600, max_points: int = 500) -> List[dict]:
    """Get time-series data for a tag over the last duration_s seconds."""
    cutoff = time.time() - duration_s
    with _db_lock:
        rows = get_db().execute(
            """SELECT value, timestamp FROM readings
               WHERE tag=? AND timestamp > ?
               ORDER BY timestamp ASC""",
            (tag, cutoff),
        ).fetchall()

    if not rows:
        return []

    # Downsample if too many points
    if len(rows) > max_points:
        step = len(rows) // max_points
        rows = rows[::step]

    return [{"value": row["value"], "timestamp": row["timestamp"]} for row in rows]


def get_all_tags_latest() -> Dict[str, dict]:
    """Get the most recent reading for every tag."""
    with _db_lock:
        rows = get_db().execute(
            """SELECT tag, value, timestamp,
                      MAX(timestamp) as max_ts
               FROM readings
               GROUP BY tag
               ORDER BY tag"""
        ).fetchall()
    return {
        row["tag"]: {"value": row["value"], "timestamp": row["timestamp"]}
        for row in rows
    }


# --- Events ---

def log_event(event_type: str, tag: str = None, message: str = None, value: float = None) -> None:
    with _db_lock:
        get_db().execute(
            "INSERT INTO events (timestamp, event_type, tag, message, value) VALUES (?, ?, ?, ?, ?)",
            (time.time(), event_type, tag, message, value),
        )
        get_db().commit()


def get_events(limit: int = 200, event_type: str = None) -> List[dict]:
    with _db_lock:
        if event_type:
            rows = get_db().execute(
                "SELECT * FROM events WHERE event_type=? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            ).fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


# --- Daily Summary ---

def generate_daily_summary(date_str: str = None) -> int:
    """Generate or update daily min/max/avg summaries. Returns count of tags summarized."""
    import datetime
    if date_str is None:
        date_str = datetime.date.today().isoformat()

    # Parse date boundaries — use date.fromisoformat so bare "YYYY-MM-DD"
    # strings work on Python 3.10 and earlier (datetime.fromisoformat only
    # accepted bare date strings from 3.11 onwards).
    day_start = datetime.datetime(
        *datetime.date.fromisoformat(date_str).timetuple()[:3]
    ).timestamp()
    day_end = day_start + 86400

    with _db_lock:
        rows = get_db().execute(
            """SELECT tag,
                      MIN(value) as min_val,
                      MAX(value) as max_val,
                      AVG(value) as avg_val,
                      COUNT(*) as cnt
               FROM readings
               WHERE timestamp >= ? AND timestamp < ?
               GROUP BY tag""",
            (day_start, day_end),
        ).fetchall()

        for row in rows:
            get_db().execute(
                """INSERT INTO daily_summary (tag, date, min_value, max_value, avg_value, sample_count)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(tag, date) DO UPDATE SET
                     min_value=excluded.min_value, max_value=excluded.max_value,
                     avg_value=excluded.avg_value, sample_count=excluded.sample_count""",
                (row["tag"], date_str, row["min_val"], row["max_val"],
                 row["avg_val"], row["cnt"]),
            )
        get_db().commit()

    return len(rows)


def get_daily_summaries(date_str: str = None) -> List[dict]:
    import datetime
    if date_str is None:
        date_str = datetime.date.today().isoformat()
    with _db_lock:
        rows = get_db().execute(
            "SELECT * FROM daily_summary WHERE date=? ORDER BY tag",
            (date_str,),
        ).fetchall()
    return [dict(row) for row in rows]


# --- Maintenance ---

def prune_old_readings(max_age_hours: int = 48) -> int:
    """Delete readings older than max_age_hours. Returns count deleted."""
    cutoff = time.time() - (max_age_hours * 3600)
    with _db_lock:
        cur = get_db().execute("DELETE FROM readings WHERE timestamp < ?", (cutoff,))
        get_db().commit()
        return cur.rowcount


def get_db_stats() -> dict:
    """Return database size info."""
    with _db_lock:
        readings_count = get_db().execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        events_count = get_db().execute("SELECT COUNT(*) FROM events").fetchone()[0]
        tags = get_db().execute("SELECT COUNT(DISTINCT tag) FROM readings").fetchone()[0]
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "readings": readings_count,
        "events": events_count,
        "tags": tags,
        "db_size_mb": round(db_size / 1024 / 1024, 2),
    }
