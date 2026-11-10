"""Chế độ phát hành của ứng dụng.

``standard`` — bản thương mại: bắt buộc dùng thử / kích hoạt mã.
``full``     — bản nội bộ đã cấp sẵn bản quyền vĩnh viễn, ẩn trang Bản quyền.

Giá trị lấy từ ``version.__edition__``; test có thể monkeypatch ``EDITION``
để kiểm tra cả hai nhánh.
"""

from __future__ import annotations

from version import __edition__

STANDARD = "standard"
FULL = "full"

EDITION = __edition__


def is_full() -> bool:
    """True khi bản build đã được cấp sẵn bản quyền vĩnh viễn."""
    return EDITION == FULL


def license_visible() -> bool:
    """Trang/mục Bản quyền chỉ hiện ở bản standard."""
    return not is_full()
