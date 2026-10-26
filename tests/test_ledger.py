"""Kiểm thử sổ key (tools/license_tool/ledger.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "license_tool"))

import ledger  # noqa: E402

BASE_TS = 1_790_000_000


def _add(db, index: int, *, customer: str = "", phone: str = "",
         machine: str = "01QGBECPG6", created: int | None = None) -> int:
    return ledger.add(
        code=f"CODE{index:03d}",
        machine=machine,
        kind=1,
        days=30,
        issued_day=250,
        expiry_day=280,
        customer=customer,
        phone=phone,
        created_at=BASE_TS + index if created is None else created,
        path=db,
    )


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "issued.sqlite"
    for i in range(150):
        _add(path, i, customer=f"Khách {i:03d}", phone=f"090{i:04d}")
    return path


def test_trang_100_ban_ghi(db):
    page1, total = ledger.query(page=1, path=db)
    page2, total2 = ledger.query(page=2, path=db)
    assert total == total2 == 150
    assert len(page1) == ledger.PAGE_SIZE == 100
    assert len(page2) == 50


def test_moi_nhat_truoc(db):
    rows, _ = ledger.query(page=1, path=db)
    times = [row["created_at"] for row in rows]
    assert times == sorted(times, reverse=True)
    assert rows[0]["id"] > rows[-1]["id"]


def test_trang_ngoai_pham_vi_tra_rong(db):
    rows, total = ledger.query(page=99, path=db)
    assert rows == []
    assert total == 150


def test_tim_theo_ten(db):
    rows, total = ledger.query("Khách 140", path=db)
    assert total == 1
    assert rows[0]["customer"] == "Khách 140"


def test_tim_khong_phan_biet_dau(db):
    rows, total = ledger.query("khach 140", path=db)
    assert total == 1
    assert rows[0]["customer"] == "Khách 140"


def test_tim_theo_sdt(db):
    rows, total = ledger.query("0900014", path=db)
    assert total == 1
    assert rows[0]["phone"] == "0900014"


def test_tim_theo_ma_may_co_dau_gach(db):
    rows, total = ledger.query("01QGB-ECPG6", path=db)
    assert total == 150
    assert len(rows) == 100


def test_tim_theo_ma_may_khong_dau_gach(db):
    _, total = ledger.query("01qgb ecpg6", path=db)
    assert total == 150


def test_tim_khong_khop(db):
    rows, total = ledger.query("không có ai", path=db)
    assert rows == []
    assert total == 0


def test_loc_roi_van_phan_trang(db):
    rows, total = ledger.query("Khách 1", page=1, path=db)
    assert total == 50
    assert len(rows) == 50
    assert rows[0]["customer"] == "Khách 149"


def test_sap_xep_theo_created_at(tmp_path):
    path = tmp_path / "issued.sqlite"
    _add(path, 1, customer="Cũ", created=BASE_TS)
    _add(path, 2, customer="Mới", created=BASE_TS + 500)
    _add(path, 3, customer="Giữa", created=BASE_TS + 250)
    rows, _ = ledger.query(path=path)
    assert [row["customer"] for row in rows] == ["Mới", "Giữa", "Cũ"]


def test_so_key_trong(tmp_path):
    path = tmp_path / "issued.sqlite"
    rows, total = ledger.query(path=path)
    assert rows == [] and total == 0
    assert ledger.count(path=path) == 0


def test_by_machine_va_find(db):
    assert len(ledger.by_machine("01QGBECPG6", path=db)) == 150
    found = ledger.find("CODE007", path=db)
    assert found is not None and found["customer"] == "Khách 007"
