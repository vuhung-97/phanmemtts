r"""Sổ key đã cấp (SQLite) — tra cứu khách, cấp lại, thống kê.

- File mặc định: `tools\license_tool\keys\issued.sqlite` khi chạy từ repo;
  `keys\issued.sqlite` cạnh exe khi đóng gói (hoặc biến `PPMTTS_LEDGER`).
- Sắp xếp mới nhất trước, mỗi trang 100 bản ghi, tìm theo tên/SĐT/mã máy
  (không phân biệt hoa thường và không phân biệt dấu tiếng Việt).
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import time
import unicodedata
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE_SIZE = 100

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


def db_path() -> Path:
    env = os.environ.get("PPMTTS_LEDGER")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "keys" / "issued.sqlite"
    return HERE / "keys" / "issued.sqlite"


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = Path(path) if path is not None else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _fold(text: str) -> str:
    """Chuẩn hoá để tìm kiếm: bỏ dấu tiếng Việt + lowercase."""
    value = unicodedata.normalize("NFD", text or "")
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return value.casefold()


def add(code: str, machine: str, kind: int, days: int, issued_day: int,
        expiry_day: int | None, customer: str = "", phone: str = "",
        note: str = "", reissued_from: int | None = None,
        created_at: int | None = None, path: Path | None = None) -> int:
    with closing(connect(path)) as conn:
        cur = conn.execute(
            "INSERT INTO issued (code, machine, kind, days, issued_day,"
            " expiry_day, customer, phone, note, created_at, reissued_from)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (code, machine, kind, int(days), int(issued_day), expiry_day,
             customer or "", phone or "", note or "",
             int(created_at if created_at is not None else time.time()),
             reissued_from),
        )
        conn.commit()
        return int(cur.lastrowid)


def _all_rows(path: Path | None = None) -> list[dict]:
    with closing(connect(path)) as conn:
        rows = conn.execute(
            "SELECT * FROM issued ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def query(keyword: str = "", page: int = 1, page_size: int = PAGE_SIZE,
          path: Path | None = None) -> tuple[list[dict], int]:
    """Trả (rows của trang, tổng số bản ghi khớp). Mới nhất trước."""
    rows = _all_rows(path)
    needle = _fold(keyword).strip()
    if needle:
        machine_needle = re.sub(r"[^0-9a-z]", "", needle)
        filtered = []
        for row in rows:
            if needle in _fold(row.get("customer", "")):
                filtered.append(row)
                continue
            if needle in _fold(row.get("phone", "")):
                filtered.append(row)
                continue
            machine = re.sub(r"[^0-9a-z]", "", _fold(row.get("machine", "")))
            if machine_needle and machine_needle in machine:
                filtered.append(row)
        rows = filtered

    total = len(rows)
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    start = (page - 1) * page_size
    return rows[start:start + page_size], total


def recent(limit: int = PAGE_SIZE, path: Path | None = None) -> list[dict]:
    with closing(connect(path)) as conn:
        rows = conn.execute(
            "SELECT * FROM issued ORDER BY created_at DESC, id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def by_machine(machine: str, path: Path | None = None) -> list[dict]:
    with closing(connect(path)) as conn:
        rows = conn.execute(
            "SELECT * FROM issued WHERE machine = ? ORDER BY created_at DESC, id DESC",
            (machine,),
        ).fetchall()
    return [dict(row) for row in rows]


def find(code: str, path: Path | None = None) -> dict | None:
    with closing(connect(path)) as conn:
        row = conn.execute(
            "SELECT * FROM issued WHERE code = ? ORDER BY created_at DESC LIMIT 1",
            (code,),
        ).fetchone()
    return dict(row) if row else None


def count(path: Path | None = None) -> int:
    with closing(connect(path)) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM issued").fetchone()
    return int(row["n"]) if row else 0
