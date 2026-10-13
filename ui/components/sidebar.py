from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.config import load_test_text, save_test_text


class Sidebar(ctk.CTkFrame):
    """Thanh bên trái: mở file, chọn giọng, test, tốc độ, chuyển đổi, xuất, trạng thái."""

    WIDTH = 240

    def __init__(
        self,
        master,
        on_open_file: Callable[[], None],
        on_voice_change: Callable[[str], None],
        on_speed_change: Callable[[float], None],
        on_convert: Callable[[], None],
        on_export: Callable[[], None],
        on_manage_voices: Callable[[], None],
        on_test_voice: Callable[[], None],
    ) -> None:
        super().__init__(master, width=self.WIDTH, corner_radius=0,
                         fg_color=theme.SIDEBAR_BG)
        self.grid_propagate(False)
        self._on_open_file = on_open_file
        self._on_voice_change = on_voice_change
        self._on_speed_change = on_speed_change
        self._on_convert = on_convert
        self._on_export = on_export
        self._on_manage_voices = on_manage_voices
        self._on_test_voice = on_test_voice

        self.grid_columnconfigure(0, weight=1)
        row = 0

        # ── Mở file ──
        ctk.CTkButton(
            self, text="📁  Mở file", height=36, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_open_file,
        ).grid(row=row, column=0, padx=16, pady=(16, 0), sticky="ew")
        row += 1

        row = self._divider(row)

        # ── Giọng đọc ──
        self._section_label("Giọng đọc", row)
        row += 1

        self.voice_combo = ctk.CTkComboBox(
            self, height=32, state="readonly", values=["(chưa có model)"],
            command=self._voice_changed, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.voice_combo.grid(row=row, column=0, padx=16, pady=(2, 6), sticky="ew")
        row += 1

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=row, column=0, padx=16, pady=(0, 4), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="＋ Thêm", height=28, width=0,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._on_manage_voices,
        ).grid(row=0, column=0, padx=(0, 3), sticky="ew")

        ctk.CTkButton(
            btn_row, text="🔊 Test", height=28, width=0,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._on_test_voice,
        ).grid(row=0, column=1, padx=(3, 0), sticky="ew")
        row += 1

        # ── Ô nhập câu test ──
        self.test_entry = ctk.CTkEntry(
            self, height=30, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            placeholder_text="Nhập câu test...",
        )
        self.test_entry.insert(0, load_test_text())
        self.test_entry.grid(row=row, column=0, padx=16, pady=(2, 4), sticky="ew")
        self.test_entry.bind("<Return>", lambda _: self._save_test_text())
        row += 1

        row = self._divider(row)

        # ── Tốc độ ──
        self._section_label("Tốc độ", row)
        row += 1

        self.speed_combo = ctk.CTkComboBox(
            self, height=32, state="readonly",
            values=["0.75x", "1.0x", "1.25x", "1.5x"],
            command=self._speed_changed, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.speed_combo.set("1.0x")
        self.speed_combo.grid(row=row, column=0, padx=16, pady=(2, 4), sticky="ew")
        row += 1

        row = self._divider(row)

        # ── Chuyển đổi / Xuất ──
        self.convert_btn = ctk.CTkButton(
            self, text="⚡  Chuyển đổi", height=38, fg_color=theme.SUCCESS,
            hover_color="#3d9a6c", corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_convert,
        )
        self.convert_btn.grid(row=row, column=0, padx=16, pady=(8, 4), sticky="ew")
        row += 1

        self.export_btn = ctk.CTkButton(
            self, text="💾  Xuất file", height=34,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_export,
        )
        self.export_btn.grid(row=row, column=0, padx=16, pady=(0, 4), sticky="ew")
        row += 1

        row = self._divider(row)

        # ── Status (cuối sidebar) ──
        self.status_label = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), wraplength=self.WIDTH - 32,
        )
        self.status_label.grid(row=100, column=0, padx=16, pady=(8, 12),
                               sticky="sew")
        self.grid_rowconfigure(100, weight=1)

    # ── helpers ──

    def _divider(self, row: int) -> int:
        frame = ctk.CTkFrame(self, height=1, fg_color=theme.SIDEBAR_DIVIDER)
        frame.grid(row=row, column=0, padx=16, pady=8, sticky="ew")
        return row + 1

    def _section_label(self, text: str, row: int) -> None:
        ctk.CTkLabel(
            self, text=text, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1, "bold"),
        ).grid(row=row, column=0, padx=16, sticky="w")

    # ── public API ──

    def set_voices(self, names: list[str], selected: str | None = None) -> None:
        self.voice_combo.configure(values=names or ["(chưa có model)"])
        if names:
            self.voice_combo.set(selected or names[0])

    def get_selected_voice(self) -> str | None:
        return self.voice_combo.get() or None

    def get_speed(self) -> float:
        return float(self.speed_combo.get().replace("x", ""))

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.convert_btn.configure(state=state)
        self.export_btn.configure(state=state)

    def set_status(self, message: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=message, text_color=color)

    def get_test_text(self) -> str:
        """Lấy câu test từ entry, lưu lại vào config."""
        text = self.test_entry.get().strip()
        if text:
            save_test_text(text)
        return text or load_test_text()

    def _save_test_text(self) -> None:
        text = self.test_entry.get().strip()
        if text:
            save_test_text(text)
            self.set_status("Đã lưu câu test.", theme.SUCCESS)

    def _voice_changed(self, value: str) -> None:
        self._on_voice_change(value)

    def _speed_changed(self, value: str) -> None:
        self._on_speed_change(float(value.replace("x", "")))
