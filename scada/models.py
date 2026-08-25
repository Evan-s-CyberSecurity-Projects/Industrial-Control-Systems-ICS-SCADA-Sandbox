"""
SQLite persistence for alarm configuration, active alarms, history, and audit trail.
"""

from __future__ import annotations

import json
import sqlite3
import time
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEFAULT_DB_PATH = Path("/data/hmi.db")


def _resolve_db_path() -> Path:
    """Return /data/hmi.db if writable, otherwise fall back to a temp dir."""
    path = _DEFAULT_DB_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        probe = path.parent / ".write_probe"
        probe.touch()
        probe.unlink()
        return path
    except OSError:
        import tempfile
        fallback = Path(tempfile.gettempdir()) / "hmi.db"
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Cannot write to %s — using fallback DB at %s", path, fallback
        )
        return fallback


DB_PATH: Path = _resolve_db_path()


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_db_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _get_db()
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS alarm_config (
            tag TEXT PRIMARY KEY,
            high_high REAL,
            high REAL,
            low REAL,
            low_low REAL,
            deadband REAL DEFAULT 1.0,
            enabled INTEGER DEFAULT 1,
            updated_at REAL
        );

        CREATE TABLE IF NOT EXISTS active_alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            level TEXT NOT NULL,
            value REAL,
            threshold REAL,
            message TEXT,
            timestamp REAL NOT NULL,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_at REAL,
            acknowledged_by TEXT
        );

        CREATE TABLE IF NOT EXISTS alarm_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,
            level TEXT NOT NULL,
            value REAL,
            threshold REAL,
            message TEXT,
            timestamp REAL NOT NULL,
            cleared_at REAL,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_at REAL,
            acknowledged_by TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            action TEXT NOT NULL,
            tag TEXT,
            details TEXT,
            old_value TEXT,
            new_value TEXT
        );
    """)
    conn.commit()


# --- Alarm Config ---

@dataclass
class AlarmConfig:
    tag: str
    high_high: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    low_low: Optional[float] = None
    deadband: float = 1.0
    enabled: bool = True


def get_alarm_config(tag: str) -> Optional[AlarmConfig]:
    with _db_lock:
        row = get_db().execute(
            "SELECT * FROM alarm_config WHERE tag=?", (tag,)
        ).fetchone()
    if not row:
        return None
    return AlarmConfig(
        tag=row["tag"],
        high_high=row["high_high"],
        high=row["high"],
        low=row["low"],
        low_low=row["low_low"],
        deadband=row["deadband"],
        enabled=bool(row["enabled"]),
    )


def get_all_alarm_configs() -> Dict[str, AlarmConfig]:
    with _db_lock:
        rows = get_db().execute("SELECT * FROM alarm_config").fetchall()
    return {
        row["tag"]: AlarmConfig(
            tag=row["tag"],
            high_high=row["high_high"],
            high=row["high"],
            low=row["low"],
            low_low=row["low_low"],
            deadband=row["deadband"],
            enabled=bool(row["enabled"]),
        )
        for row in rows
    }


def set_alarm_config(config: AlarmConfig) -> None:
    with _db_lock:
        get_db().execute(
            """INSERT INTO alarm_config (tag, high_high, high, low, low_low, deadband, enabled, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(tag) DO UPDATE SET
                 high_high=excluded.high_high, high=excluded.high,
                 low=excluded.low, low_low=excluded.low_low,
                 deadband=excluded.deadband, enabled=excluded.enabled,
                 updated_at=excluded.updated_at""",
            (config.tag, config.high_high, config.high, config.low, config.low_low,
             config.deadband, int(config.enabled), time.time()),
        )
        get_db().commit()


# --- Active Alarms ---

@dataclass
class ActiveAlarm:
    id: int
    tag: str
    level: str
    value: float
    threshold: float
    message: str
    timestamp: float
    acknowledged: bool = False
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None


def add_active_alarm(tag: str, level: str, value: float, threshold: float, message: str) -> int:
    with _db_lock:
        cur = get_db().execute(
            """INSERT INTO active_alarms (tag, level, value, threshold, message, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tag, level, value, threshold, message, time.time()),
        )
        get_db().commit()
        return cur.lastrowid


def get_active_alarms() -> List[ActiveAlarm]:
    with _db_lock:
        rows = get_db().execute(
            "SELECT * FROM active_alarms ORDER BY timestamp DESC"
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["acknowledged"] = bool(d.get("acknowledged", 0))
        result.append(ActiveAlarm(**d))
    return result


def acknowledge_alarm(alarm_id: int, by: str = "operator") -> None:
    now = time.time()
    with _db_lock:
        get_db().execute(
            """UPDATE active_alarms SET acknowledged=1, acknowledged_at=?, acknowledged_by=?
               WHERE id=?""",
            (now, by, alarm_id),
        )
        get_db().commit()


def acknowledge_all_alarms(by: str = "operator") -> int:
    now = time.time()
    with _db_lock:
        cur = get_db().execute(
            """UPDATE active_alarms SET acknowledged=1, acknowledged_at=?, acknowledged_by=?
               WHERE acknowledged=0""",
            (now, by),
        )
        get_db().commit()
        return cur.rowcount


def clear_alarm(alarm_id: int) -> None:
    """Move an alarm from active to history."""
    with _db_lock:
        db = get_db()
        row = db.execute("SELECT * FROM active_alarms WHERE id=?", (alarm_id,)).fetchone()
        if row:
            db.execute(
                """INSERT INTO alarm_history
                   (tag, level, value, threshold, message, timestamp, cleared_at,
                    acknowledged, acknowledged_at, acknowledged_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row["tag"], row["level"], row["value"], row["threshold"],
                 row["message"], row["timestamp"], time.time(),
                 row["acknowledged"], row["acknowledged_at"], row["acknowledged_by"]),
            )
            db.execute("DELETE FROM active_alarms WHERE id=?", (alarm_id,))
            db.commit()


def is_alarm_active(tag: str, level: str) -> bool:
    with _db_lock:
        row = get_db().execute(
            "SELECT id FROM active_alarms WHERE tag=? AND level=?", (tag, level)
        ).fetchone()
    return row is not None


def get_alarm_history(limit: int = 200) -> List[dict]:
    with _db_lock:
        rows = get_db().execute(
            "SELECT * FROM alarm_history ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["acknowledged"] = bool(d.get("acknowledged", 0))
        result.append(d)
    return result


# --- Audit Log ---

def audit(action: str, tag: str = None, details: str = None,
          old_value: str = None, new_value: str = None) -> None:
    with _db_lock:
        get_db().execute(
            """INSERT INTO audit_log (timestamp, action, tag, details, old_value, new_value)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (time.time(), action, tag, details, old_value, new_value),
        )
        get_db().commit()


def get_audit_log(limit: int = 200) -> List[dict]:
    with _db_lock:
        rows = get_db().execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]
