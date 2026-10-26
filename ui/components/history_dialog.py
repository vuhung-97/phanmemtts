"""Dialog Lịch sử bản dựng: nghe lại / mở thư mục / xoá."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from core.history import HistoryStore
from ui import theme


def open_in_system(path: Path) -> None:
    """Mở file/thư mục bằng ứng dụng mặc định của hệ điều hành."""
    try:
        if os.name == "nt":
            os.startfile(str(path))          # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


class HistoryDialog(ctk.CTkToplevel):
    """Danh sách các lần xuất file, mới nhất ở trên."""

    def __init__(self, master, store: HistoryStore) -> None:
        super().__init__(master)
        self.title("Lịch sử bản dựng")
        self.geometry("760x560")
        self.minsize(620, 420)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._store = store
        self._build_ui()
        self._rebuild()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _: self.destroy())

    # ── UI ──

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, padx=18, pady=(14, 6), sticky="ew")
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            head, text="🕘  Lịch sử bản dựng",
            font=(theme.FONT_FAMILY, theme.TITLE_SIZE + 1, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w")

        self.summary_label = ctk.CTkLabel(
            head, text="", text_color=theme.TEXT_DIM, anchor="e",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.summary_label.grid(row=0, column=1, sticky="e")

        self.notice_label = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM, anchor="w",
            wraplength=700, justify="left",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.notice_label.grid(row=1, column=0, padx=18, sticky="ew")

        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        self.list_frame.grid(row=2, column=0, padx=12, pady=(6, 6), sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=18, pady=(0, 14), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self.clear_btn = ctk.CTkButton(
            bottom, text="🗑  Xoá tất cả", height=34, width=140,
            fg_color="transparent", border_width=1, border_color=theme.ERROR,
            text_color=theme.ERROR, hover_color=theme.HOVER_BG, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), command=self._clear_all,
        )
        self.clear_btn.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            bottom, text="Đóng", height=34, width=120,
            fg_color=theme.DARK_BUTTON_BG, hover_color=theme.DARK_BUTTON_HOVER,
            text_color=theme.DARK_BUTTON_TEXT, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self.destroy,
        ).grid(row=0, column=1, sticky="e")

    # ── Dựng danh sách ──

    def _rebuild(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()

        entries = self._store.entries
        self.summary_label.configure(
            text=f"{len(entries)} bản · {self._store.total_size_text()}")
        self.clear_btn.configure(state="normal" if entries else "disabled")

        if self._store.is_large():
            self.notice_label.configure(
                text="⚠ Lịch sử đã vượt 500 MB — nên xoá bớt bản cũ. "
                     "Hệ thống tự xoá bản cũ nhất khi vượt 1 GB.",
                text_color=theme.ERROR)
        else:
            self.notice_label.configure(
                text="Mỗi bản là một bản sao trong thư mục dữ liệu; "
                     "xoá ở đây không ảnh hưởng file bạn đã xuất.",
                text_color=theme.TEXT_DIM)

        if not entries:
            ctk.CTkLabel(
                self.list_frame, text="Chưa có bản dựng nào.\n"
                                      "Hãy chuyển đổi rồi bấm «Xuất file».",
                text_color=theme.TEXT_DIM, justify="left",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            ).grid(row=0, column=0, padx=10, pady=30, sticky="w")
            return

        for row, entry in enumerate(entries):
            self._build_row(row, entry)

    def _build_row(self, row: int, entry) -> None:
        card = ctk.CTkFrame(self.list_frame, fg_color=theme.SURFACE,
                            corner_radius=8, border_width=1,
                            border_color=theme.SIDEBAR_DIVIDER)
        card.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=entry.created_text, text_color=theme.TEXT, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
        ).grid(row=0, column=0, padx=(12, 6), pady=(8, 0), sticky="w")

        meta = (f"Giọng: {entry.voice or '—'} · {entry.speed_text} · "
                f"{entry.duration_text} · {entry.size_text}")
        ctk.CTkLabel(
            card, text=meta, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        ).grid(row=1, column=0, padx=(12, 6), sticky="w")

        preview = entry.preview or "(không có văn bản)"
        ctk.CTkLabel(
            card, text=preview, text_color=theme.TEXT_DIM, anchor="w",
            justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        ).grid(row=2, column=0, padx=(12, 6), pady=(2, 8), sticky="w")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=3, padx=(6, 10), pady=8, sticky="e")

        ctk.CTkButton(
            actions, text="▶  Nghe", height=30, width=86,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.HOVER_BG, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=lambda e=entry: self._play(e),
        ).grid(row=0, column=0, padx=(0, 4))

        ctk.CTkButton(
            actions, text="📂", height=30, width=40,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.HOVER_BG, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=lambda e=entry: open_in_system(self._store.audio_path(e).parent),
        ).grid(row=0, column=1, padx=(0, 4))

        ctk.CTkButton(
            actions, text="🗑", height=30, width=40,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.ERROR, hover_color=theme.HOVER_BG, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=lambda e=entry: self._delete(e),
        ).grid(row=0, column=2)

    # ── Hành động ──

    def _play(self, entry) -> None:
        path = self._store.audio_path(entry)
        if not path.exists():
            messagebox.showwarning(
                "Thiếu file",
                "Bản ghi này đã mất file audio (có thể bị xoá thủ công).\n"
                "Hãy xoá bản ghi khỏi lịch sử.",
                parent=self,
            )
            return
        open_in_system(path)

    def _delete(self, entry) -> None:
        if not messagebox.askyesno(
            "Xoá bản ghi",
            f"Xoá bản dựng {entry.created_text} khỏi lịch sử?\n"
            "(File bạn đã xuất ra ngoài vẫn còn.)",
            parent=self,
        ):
            return
        self._store.remove(entry.id)
        self._rebuild()

    def _clear_all(self) -> None:
        entries = self._store.entries
        if not entries:
            return
        if not messagebox.askyesno(
            "Xoá tất cả",
            f"Xoá toàn bộ {len(entries)} bản dựng trong lịch sử "
            f"({self._store.total_size_text()})?\n"
            "(File bạn đã xuất ra ngoài vẫn còn.)",
            parent=self,
        ):
            return
        self._store.clear()
        self._rebuild()
