"""Hộp thoại Điều khoản sử dụng & Quyền riêng tư.

Lần chạy đầu: bắt buộc tick "Tôi đã đọc và đồng ý" mới dùng được phần mềm.
Về sau: mở từ menu Trợ giúp để xem lại (chỉ đọc).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from core.paths import app_dir, resource_path
from ui import theme

TERMS_VERSION = 1
TERMS_FILES = ("DIEU-KHOAN.md", "PRIVACY.md")

_FALLBACK = (
    "Phần mềm chạy hoàn toàn offline, không gửi dữ liệu ra ngoài.\n\n"
    "Bạn cam kết chỉ dùng giọng nói của chính mình hoặc giọng đã được "
    "cho phép sử dụng, và tự chịu trách nhiệm về nội dung tạo ra.\n\n"
    "Chưa kích hoạt vẫn chuyển đổi và nghe thử được; khoá xuất tệp và "
    "ghép nhạc.\n"
)


def terms_text() -> str:
    """Đọc nội dung điều khoản đi kèm; thiếu tệp -> bản tóm tắt."""
    chunks: list[str] = []
    for name in TERMS_FILES:
        for base in (app_dir(), resource_path(".")):
            path = Path(base) / name
            if path.is_file():
                try:
                    chunks.append(path.read_text(encoding="utf-8-sig").strip())
                except OSError:
                    pass
                break
    if not chunks:
        return _FALLBACK
    return "\n\n──────────────────────────────\n\n".join(chunks)


class TermsDialog(ctk.CTkToplevel):
    """Hiển thị điều khoản; ``require_accept`` = bắt buộc đồng ý để tiếp tục."""

    def __init__(self, master, require_accept: bool = True,
                 on_accept: Callable[[], None] | None = None) -> None:
        super().__init__(master)
        self.result = False
        self._require_accept = require_accept
        self._on_accept = on_accept

        self.title("Điều khoản sử dụng & Quyền riêng tư")
        self.geometry("760x660")
        self.minsize(620, 520)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._decline)
        self.bind("<Escape>", lambda _: self._decline())

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, padx=18, pady=(14, 4), sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            head, text="Điều khoản sử dụng & Quyền riêng tư",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 3, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head,
            text=("Phần mềm chạy offline, không gửi dữ liệu ra ngoài. "
                  f"Phiên bản điều khoản: {TERMS_VERSION}."),
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        ).grid(row=1, column=0, pady=(2, 0), sticky="w")

        self.body = ctk.CTkTextbox(
            self, fg_color=theme.SURFACE, text_color=theme.TEXT,
            border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), wrap="word",
        )
        self.body.grid(row=1, column=0, padx=18, pady=6, sticky="nsew")
        self.body.insert("1.0", terms_text())
        self.body.configure(state="disabled")

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, padx=18, pady=(4, 16), sticky="ew")
        foot.grid_columnconfigure(0, weight=1)

        self.accept_var = ctk.BooleanVar(value=False)
        self.accept_check = ctk.CTkCheckBox(
            foot, text="Tôi đã đọc và đồng ý với điều khoản sử dụng ở trên",
            variable=self.accept_var, command=self._sync_accept_button,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            text_color=theme.TEXT, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT, corner_radius=4,
        )
        self.accept_check.grid(row=0, column=0, columnspan=2, pady=(0, 8), sticky="w")

        if not self._require_accept:
            self.accept_var.set(True)
            self.accept_check.grid_remove()

        self.decline_btn = ctk.CTkButton(
            foot, text="Không đồng ý", height=36, width=130,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT_DIM, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._decline,
        )
        self.decline_btn.grid(row=1, column=0, sticky="w")

        self.accept_btn = ctk.CTkButton(
            foot,
            text=("Đồng ý và tiếp tục" if self._require_accept else "Đóng"),
            height=36, width=170,
            fg_color=theme.SUCCESS if self._require_accept else theme.DARK_BUTTON_BG,
            hover_color=(theme.SUCCESS_HOVER if self._require_accept
                         else theme.DARK_BUTTON_HOVER),
            text_color="#ffffff", corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._accept,
        )
        self.accept_btn.grid(row=1, column=1, sticky="e")
        self._sync_accept_button()

    def _sync_accept_button(self) -> None:
        if not self._require_accept:
            self.accept_btn.configure(state="normal")
            return
        self.accept_btn.configure(
            state="normal" if self.accept_var.get() else "disabled")

    def _accept(self) -> None:
        if self._require_accept and not self.accept_var.get():
            return
        self.result = True
        if self._on_accept is not None:
            self._on_accept()
        self._close()

    def _decline(self) -> None:
        self.result = False
        self._close()

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
