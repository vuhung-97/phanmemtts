from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from ui import theme
from ui.shell.page import Page
from ui.ui_kit import Badge, Button, Card


def _open_in_system(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))          # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


class HistoryPage(Page):
    """Trang Lịch sử bản dựng: nghe lại / mở thư mục / xoá."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="history",
                         title="Lịch sử bản dựng",
                         subtitle="Bản sao các file đã xuất", **kwargs)
        self._store = ctx._history

        self.clear_btn = Button(self.header.actions, text="Xoá tất cả",
                                variant="danger-soft",
                                command=self._clear_all)
        self.clear_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        Button(self.header.actions, text="Mở thư mục",
               variant="secondary", command=self._open_folder).pack(side="left")

        self.body.grid_rowconfigure(2, weight=1)

        self.summary_label = ctk.CTkLabel(
            self.body, text="", anchor="w", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.summary_label.grid(row=0, column=0, sticky="w")

        self.notice_label = ctk.CTkLabel(
            self.body, text="", anchor="w", justify="left", wraplength=860,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        )
        self.notice_label.grid(row=1, column=0, pady=(2, theme.SPACE_SM),
                               sticky="w")

        self.list_frame = ctk.CTkScrollableFrame(self.body, fg_color="transparent",
                                                 corner_radius=0)
        self.list_frame.grid(row=2, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

    # ── dựng danh sách ──

    def on_show(self) -> None:
        self._rebuild()

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
                self.list_frame,
                text="Chưa có bản dựng nào.\nHãy chuyển đổi rồi bấm «Xuất file».",
                text_color=theme.TEXT_DIM, justify="left",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            ).grid(row=0, column=0, padx=theme.SPACE_MD,
                   pady=theme.SPACE_2XL, sticky="w")
            return

        for row, entry in enumerate(entries):
            self._build_row(row, entry)

    def _build_row(self, row: int, entry) -> None:
        card = Card(self.list_frame, padding=theme.SPACE_MD)
        card.grid(row=row, column=0, sticky="ew", padx=2,
                  pady=(0, theme.SPACE_SM))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=entry.created_text, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w")

        meta = (f"Giọng: {entry.voice or '—'} · {entry.speed_text} · "
                f"{entry.duration_text} · {entry.size_text}")
        ctk.CTkLabel(
            card, text=meta, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        ).grid(row=1, column=0, sticky="w")

        ctk.CTkLabel(
            card, text=entry.preview or "(không có văn bản)", anchor="w",
            justify="left", wraplength=620,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        ).grid(row=2, column=0, pady=(2, 0), sticky="w")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=3, padx=(theme.SPACE_SM, 0),
                     sticky="e")
        Button(actions, text="▶  Nghe", variant="soft", size="sm", width=84,
               command=lambda e=entry: self._play(e)).pack(side="left",
                                                           padx=(0, theme.SPACE_XS))
        Button(actions, text="📂", variant="secondary", size="sm", width=36,
               command=lambda e=entry: _open_in_system(
                   self._store.audio_path(e).parent)).pack(side="left",
                                                           padx=(0, theme.SPACE_XS))
        Button(actions, text="🗑", variant="ghost", size="sm", width=36,
               command=lambda e=entry: self._delete(e)).pack(side="left")

    # ── hành động ──

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
        _open_in_system(path)

    def _delete(self, entry) -> None:
        if not messagebox.askyesno(
                "Xoá bản ghi",
                f"Xoá bản dựng {entry.created_text} khỏi lịch sử?\n"
                "(File bạn đã xuất ra ngoài vẫn còn.)",
                parent=self):
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
                parent=self):
            return
        self._store.clear()
        self._rebuild()

    def _open_folder(self) -> None:
        _open_in_system(self._store.root)
