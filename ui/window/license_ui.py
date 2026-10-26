"""Phần bản quyền của MainWindow (badge, hộp thoại, freemium gate).

Tách khỏi main_window.py để giữ mỗi file dưới giới hạn 32 KB của PyArmor.
"""

from __future__ import annotations

from core.licensing import guard, trial
from ui import theme


class LicenseMixin:
    def _refresh_license_badge(self, status=None):
        """Cập nhật nhãn 🔑 trên thanh menu theo trạng thái hiện tại."""
        status = status or guard.check_startup(use_cache=False)
        color = theme.TEXT_DIM
        left = status.days_left
        if not status.active:
            color = theme.ERROR
        elif left is not None and left <= 1:
            color = theme.ERROR
        elif left is not None and left <= 7:
            color = "#b7791f"
        self.topbar.set_license(status.badge_text(), color)
        self.topbar.set_export_locked(not status.active)
        return status

    def _open_license_dialog(self) -> None:
        from ui.components.license_dialog import LicenseDialog

        LicenseDialog(self, on_activate=self._open_activation)
        self._refresh_license_badge()

    def _open_activation(self) -> bool:
        from ui.components.activation_dialog import ask_activation

        ok = ask_activation(self, status=guard.check_startup(use_cache=False))
        self._refresh_license_badge()
        if ok and not self._all_models:
            self._scan_models()
        return ok

    def _ensure_license(self, feature: str = "") -> bool:
        """Chặn tính năng tạo ra file khi chưa kích hoạt; mở hộp thoại nếu cần."""
        status = guard.check_startup(use_cache=False)
        if status.active:
            return True
        self._refresh_license_badge(status)
        if feature:
            message = f"Cần kích hoạt để {feature}."
        else:
            message = status.message or "Thiết bị chưa được kích hoạt."
        self.topbar.set_status(message, theme.ERROR)
        return self._open_activation()

    def _first_run_prompt(self) -> None:
        """Lần chạy đầu: mời dùng thử / nhập mã (vẫn đóng được để dùng tiếp)."""
        status = guard.check_startup(use_cache=False)
        if status.active:
            return
        info = trial.info()
        if info.started:
            self.topbar.set_status(
                "Đã hết hạn dùng thử — vẫn nghe thử được, cần mã để xuất file.",
                theme.ERROR)
            return
        if not info.can_start:
            self.topbar.set_status(
                "Chưa kích hoạt — vẫn nghe thử được, cần mã để xuất file.",
                theme.TEXT_DIM)
            return
        if not self._open_activation():
            self.topbar.set_status(
                "Chưa kích hoạt — vẫn nghe thử được, cần mã để xuất file.",
                theme.TEXT_DIM)

