"""Sá»• key Ä‘Ã£ cáº¥p (SQLite) â€” tra cá»©u khÃ¡ch, cáº¥p láº¡i, thá»‘ng kÃª.

File máº·c Ä‘á»‹nh: tools/license_tool/keys/issued.sqlite (cÃ¹ng thÆ° má»¥c vá»›i secret,
Ä‘Ã£ gitignore â€” nÃªn backup chung cáº£ thÆ° má»¥c keys/).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "keys" / "issued.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS issued (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    machine TEXT NOT NULL,
    kind INTEGER NOT NULL,
    days INTEGER NOT NULL,
    issued_day INTEGER NOT NULL,
    expiry_day INTEGER,
    customer TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at INTEGER NOT NULL,
    reissued_from INTEGER
);
CREATE INDEX IF NOT EXISTS idx_issued_machine ON issued(machine);
CREATE INDEX IF NOT EXISTS idx_issued_created ON issued(created_at);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = Path(path) if path is not None else DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def add(code: str, machine: str, kind: int, days: int, issued_day: int,
        expiry_day: int | None, customer: str = "", phone: str = "",
        note: str = "", reissued_from: int | None = None,
        path: Path | None = None) -> int:
    with closing(connect(path)) as conn:
        cur = conn.execute(
            "INSERT INTO issued (code, machine, kind, days, issued_day,"
            " expiry_day, customer, phone, note, created_at, reissued_from)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (code, machine, kind, int(days), int(issued_day), expiry_day,
             customer or "", phone or "", note or "", int(time.time()),
             reissued_from),
        )
        conn.commit()
        return int(cur.lastrowid)


def recent(limit: int = 200, path: Path | None = None) -> list[dict]:
    with closing(connect(path)) as conn:
        rows = conn.execute(
            "SELECT * FROM issued ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()
    return [dict(row) for row in rows]


def by_machine(machine: str, path: Path | None = None) -> list[dict]:
    with closing(connect(path)) as conn:
        rows = conn.execute(
            "SELECT * FROM issued WHERE machine = ? ORDER BY id DESC",
            (machine,),
        ).fetchall()
    return [dict(row) for row in rows]


def find(code: str, path: Path | None = None) -> dict | None:
    with closing(connect(path)) as conn:
        row = conn.execute(
            "SELECT * FROM issued WHERE code = ? ORDER BY id DESC LIMIT 1",
            (code,),
        ).fetchone()
    return dict(row) if row else None


def count(path: Path | None = None) -> int:
    with closing(connect(path)) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM issued").fetchone()
    return int(row["n"]) if row else 0


def total_days_left(path: Path | None = None) -> int:
    """Tá»•ng sá»‘ ngÃ y cÃ²n láº¡i cá»§a cÃ¡c key cÃ³ háº¡n (chá»‰ Ä‘á»ƒ xem nhanh)."""
    from core.licensing import shortcode

    today = shortcode.day_index(shortcode.utc_today())
    total = 0
    for item in recent(1000, path):
        if item.get("expiry_day") is None:
            continue
        total += max(0, int(item["expiry_day"]) - today)
    return total
