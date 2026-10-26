"""Hộp thoại kích hoạt bản quyền (mã máy 10 ký tự + mã kích hoạt 15 ký tự)."""

from __future__ import annotations

import json
import time
from tkinter import filedialog

import customtkinter as ctk

import version
from core.licensing import fingerprint, guard, store, trial
from ui import theme


def ask_activation(parent=None,
                   status: guard.LicenseStatus | None = None) -> bool:
    """Mở hộp thoại kích hoạt; trả về True nếu máy đã kích hoạt/dùng thử.

    Nếu chưa có cửa sổ nào (lúc khởi động), tự tạo một root ẩn rồi huỷ.
    """
    if parent is None:
        root = ctk.CTk()
        root.withdraw()
        try:
            dialog = ActivationDialog(root, status=status)
            root.wait_window(dialog)
            return bool(dialog.result and dialog.result.active)
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    dialog = ActivationDialog(parent, status=status)
    try:
        parent.wait_window(dialog)
    except Exception:
        pass
    return bool(dialog.result and dialog.result.active)


class ActivationDialog(ctk.CTkToplevel):
    """Modal: hiện mã máy, nhận mã 15 ký tự hoặc file .lic, hoặc bắt đầu dùng thử."""

    def __init__(self, master, status: guard.LicenseStatus | None = None) -> None:
        super().__init__(master)
        self.title("Kích hoạt bản quyền")
        self.geometry("640x500")
        self.resizable(False, False)
        self.configure(fg_color=theme.DIALOG_BG)
        # Chỉ đặt transient khi master đang hiện: nếu master bị withdraw (lúc
        # khởi động chưa có cửa sổ chính), Windows sẽ ẩn luôn hộp thoại.
        if master is not None and master.winfo_viewable():
            self.transient(master)
        self.grab_set()

        self.result: guard.LicenseStatus | None = None
        self._status = status or guard.check_startup()
        self._machine = fingerprint.format_machine_code()
        self._lock_job: str | None = None

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _: self._on_close())
        self.after(150, self.key_entry.focus_set)
        self.lift()
        self._refresh_lock()

    # ── UI ──

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Kích hoạt bản quyền",
            font=(theme.FONT_FAMILY, theme.TITLE_SIZE + 3, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=24, pady=(20, 2), sticky="w")

        self.notice = ctk.CTkLabel(
            self, text=self._status.message or "Thiết bị chưa được kích hoạt.",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            text_color=theme.TEXT_DIM, anchor="w", wraplength=580,
        )
        self.notice.grid(row=1, column=0, padx=24, pady=(0, 12), sticky="w")

        # ── Mã máy ──
        ctk.CTkLabel(
            self, text="Mã máy của bạn",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).grid(row=2, column=0, padx=24, sticky="w")

        may = ctk.CTkFrame(self, fg_color="transparent")
        may.grid(row=3, column=0, padx=24, pady=(2, 0), sticky="ew")
        may.grid_columnconfigure(0, weight=1)

        self.machine_entry = ctk.CTkEntry(
            may, height=34, font=(theme.FONT_FAMILY, theme.FONT_SIZE + 3, "bold"),
            fg_color=theme.INPUT_BG, text_color=theme.TEXT,
            border_color=theme.SIDEBAR_DIVIDER,
        )
        self.machine_entry.insert(0, self._machine)
        self.machine_entry.configure(state="readonly")
        self.machine_entry.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            may, text="Sao chép", width=96, height=34,
            fg_color=theme.BUTTON_BG, hover_color=theme.BUTTON_HOVER,
            text_color=theme.TEXT, border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._copy_machine,
        ).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkLabel(
            self, text="Gửi mã máy trên cho nhà phát triển để nhận mã kích hoạt.",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM, anchor="w",
        ).grid(row=4, column=0, padx=24, pady=(4, 14), sticky="w")

        # ── Mã kích hoạt ──
        ctk.CTkLabel(
            self, text="Mã kích hoạt (15 ký tự)",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).grid(row=5, column=0, padx=24, sticky="w")

        self.key_entry = ctk.CTkEntry(
            self, height=38, font=(theme.FONT_FAMILY, theme.FONT_SIZE + 2),
            fg_color=theme.INPUT_BG, text_color=theme.TEXT,
            border_color=theme.SIDEBAR_DIVIDER,
            placeholder_text="7K2QF-9M3XA-B8T1Z",
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
        )
        self.key_entry.grid(row=6, column=0, padx=24, pady=(2, 6), sticky="ew")
        self.key_entry.bind("<Return>", lambda _e: self._activate())

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=7, column=0, padx=24, sticky="w")
        ctk.CTkButton(
            row, text="Dán từ clipboard", width=150, height=30,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=self._paste,
        ).pack(side="left")
        ctk.CTkButton(
            row, text="Nhập từ file .lic…", width=160, height=30,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=self._load_file,
        ).pack(side="left", padx=(8, 0))

        # ── Lỗi ──
        self.error_label = ctk.CTkLabel(
            self, text="", text_color=theme.ERROR, anchor="w", wraplength=580,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.error_label.grid(row=8, column=0, padx=24, pady=(10, 0), sticky="w")

        # ── Nút ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=9, column=0, padx=24, pady=(16, 16), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        info = trial.info()
        self.trial_btn = ctk.CTkButton(
            bottom, text="🕐  Dùng thử 7 ngày", width=190, height=38,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._use_trial,
        )
        self.trial_btn.grid(row=0, column=0, sticky="w")
        if not info.can_start:
            self.trial_btn.grid_remove()

        self.activate_btn = ctk.CTkButton(
            bottom, text="🔓  Kích hoạt", width=170, height=38,
            fg_color=theme.SUCCESS, hover_color=theme.SUCCESS_HOVER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._activate,
        )
        self.activate_btn.grid(row=0, column=1, sticky="e")

    # ── Hành động ──

    def _copy_machine(self) -> None:
        text = f"Mã máy: {self._machine} | Phiên bản: {version.__version__}"
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.notice.configure(text="Đã sao chép mã máy vào clipboard.",
                                  text_color=theme.SUCCESS)
        except Exception:
            self._show_error("Không sao chép được vào clipboard.")

    def _paste(self) -> None:
        try:
            text = self.clipboard_get()
        except Exception:
            self._show_error("Clipboard đang trống.")
            return
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, (text or "").strip())
        self.key_entry.focus_set()

    def _load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file mã kích hoạt",
            filetypes=[("Mã kích hoạt", "*.lic;*.json;*.txt"),
                       ("Tất cả", "*.*")],
        )
        if not path:
            return
        try:
            raw = open(path, "r", encoding="utf-8-sig").read()
        except OSError as exc:
            self._show_error(f"Không đọc được file: {exc}")
            return
        code = raw.strip()
        if code.startswith("{"):
            try:
                code = str(json.loads(code).get("code") or "").strip()
            except ValueError:
                code = ""
        if not code:
            self._show_error("File không chứa mã kích hoạt hợp lệ.")
            return
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, code)
        self._activate()

    def _use_trial(self) -> None:
        info = trial.info()
        if not info.can_start:
            self._show_error("Máy này đã dùng thử hoặc đã hết hạn dùng thử.")
            return
        trial.start()
        status = guard.check_startup(use_cache=False)
        if status.active:
            self.result = status
            self.destroy()

    def _activate(self) -> None:
        text = self.key_entry.get().strip()
        if not text:
            self._show_error("Vui lòng nhập mã kích hoạt.")
            return
        try:
            status = guard.install(text, now=time.time())
        except guard.LicenseError as exc:
            self._show_error(str(exc))
            if exc.status is not None and exc.status.state == guard.RATE_LIMITED:
                self._refresh_lock()
            self.key_entry.select_range(0, "end")
            self.key_entry.focus_set()
            return

        if not status.active:
            self._show_error(status.message or "Mã kích hoạt không dùng được.")
            return

        self.result = status
        self.destroy()

    # ── Trạng thái phụ ──

    def _show_error(self, message: str) -> None:
        self.error_label.configure(text=message)

    def _refresh_lock(self) -> None:
        if self._lock_job is not None:
            try:
                self.after_cancel(self._lock_job)
            except Exception:
                pass
            self._lock_job = None

        remaining = store.lock_remaining()
        if remaining > 0:
            self.activate_btn.configure(state="disabled",
                                        text=f"Thử lại sau {remaining}s")
            self._lock_job = self.after(1000, self._refresh_lock)
        else:
            self.activate_btn.configure(state="normal", text="🔓  Kích hoạt")

    def _on_close(self) -> None:
        if self._lock_job is not None:
            try:
                self.after_cancel(self._lock_job)
            except Exception:
                pass
            self._lock_job = None
        self.destroy()
