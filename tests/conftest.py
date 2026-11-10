"""Thiết lập đường dẫn import cho pytest (chạy từ thư mục gốc dự án)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _standard_edition(monkeypatch):
    """Bộ test chạy ở bản standard; full edition có test riêng."""
    from core.licensing import edition, guard

    monkeypatch.setattr(edition, "EDITION", edition.STANDARD, raising=False)
    guard.reset_cache()
    yield
    guard.reset_cache()
