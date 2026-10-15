from __future__ import annotations

from typing import Callable

import customtkinter as ctk
from PIL import Image

from core.paths import resource_path
from ui import theme
from ui.config import load_test_text, save_test_text

_LOGO_PATH = resource_path("logo/logo.jpg")

# Tạm ẩn chức năng ghép nhạc: TopBar không render nút Ghép nhạc.
# Muốn bật lại: quay về Sidebar cũ, hoặc thêm nút gọi on_merge ở đây.
SHOW_MERGE = False

_NO_FILE_TEXT = "(chưa mở văn bản)"


class TopBar(ctk.CTkFrame):
    """Header 3 hàng, các nhóm nút nằm trong panel có viền:
    Hàng 1: logo | nguồn văn bản | khối hành động.
    Hàng 2: giọng đọc | nghe thử + tốc độ.
    Hàng 3: dòng thông báo riêng full-width.
    """

    def __init__(
        self,
        master,
        on_open_file: Callable[[], None],
        on_voice_change: Callable[[str], None],
        on_speed_change: Callable[[float], None],
        on_convert: Callable[[], None],
        on_stop: Callable[[], None],
        on_export: Callable[[], None],
        on_manage_voices: Callable[[], None],
        on_test_voice: Callable[[], None],
        on_merge: Callable[[], None] | None = None,  # giữ để tương thích, hiện không dùng
    ) -> None:
        super().__init__(master, corner_radius=0, fg_color=theme.SIDEBAR_BG)
        self._on_open_file = on_open_file
        self._on_voice_change = on_voice_change
        self._on_speed_change = on_speed_change
        self._on_convert = on_convert
        self._on_stop = on_stop
        self._on_export = on_export
        self._on_manage_voices = on_manage_voices
        self._on_test_voice = on_test_voice
        self._on_merge = on_merge

        # Cột 3 (panel nghe thử) giãn nở theo chiều ngang
        self.grid_columnconfigure(3, weight=1)

        # ── Panel thương hiệu: logo full chiều cao 3 hàng ──
        self._brand_outer = ctk.CTkFrame(
            self, fg_color=theme.SURFACE,
            border_width=1, border_color=theme.SIDEBAR_DIVIDER, corner_radius=10,
        )
        self._brand_outer.grid(row=0, column=0, rowspan=3, padx=5, pady=(8, 4), sticky="nsew")
        self._logo_label = ctk.CTkLabel(self._brand_outer, text="")
        self._logo_label.pack(fill="both", expand=True, padx=8, pady=6)
        self._logo_pil = None
        self._logo_h = 0
        if _LOGO_PATH.exists():
            try:
                with Image.open(_LOGO_PATH) as im:
                    im.load()
                    rgb = im.convert("RGB")
                    self._logo_pil = rgb.copy()
                self._set_logo(120)  # hiện ngay, tinh chỉnh lại khi layout xong
                self._brand_outer.bind("<Configure>", self._fit_logo)
                for _ms in (150, 600, 1500):
                    self.after(_ms, self._fit_logo)
            except Exception:
                self._logo_pil = None

        # ── Panel nguồn văn bản: nút + tên file chung 1 dòng ──
        src = self._panel(row=0, column=1, columnspan=3, sticky="ew")
        src.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            src, text="📁  Mở file", height=32, fg_color=theme.BUTTON_BG,
            hover_color=theme.BUTTON_HOVER, corner_radius=8,
            text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_open_file,
        ).grid(row=0, column=0, sticky="w")
        self.source_label = ctk.CTkLabel(
            src, text=_NO_FILE_TEXT, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.source_label.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        # ── Panel giọng đọc: combo + thêm + tốc độ ──
        voice = self._panel(row=1, column=1, columnspan=2, sticky="w")
        ctk.CTkLabel(
            voice, text="Giọng đọc", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1, "bold"),
        ).pack(side="left", padx=(0, 4))
        self.voice_combo = ctk.CTkComboBox(
            voice, height=32, width=180, state="readonly", values=["(chưa có model)"],
            command=self._voice_changed, corner_radius=6,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            button_color=theme.SURFACE, button_hover_color=theme.ACCENT,
            dropdown_fg_color=theme.INPUT_BG,
            dropdown_text_color=theme.INPUT_TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.voice_combo.pack(side="left")
        ctk.CTkButton(
            voice, text="＋ Thêm", height=32, width=76,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._on_manage_voices,
        ).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(
            voice, text="Tốc độ", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1, "bold"),
        ).pack(side="left", padx=(10, 4))
        self.speed_combo = ctk.CTkComboBox(
            voice, height=32, width=96, state="readonly",
            values=["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x"],
            command=self._speed_changed, corner_radius=6,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            button_color=theme.SURFACE, button_hover_color=theme.ACCENT,
            dropdown_fg_color=theme.INPUT_BG,
            dropdown_text_color=theme.INPUT_TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.speed_combo.set("1.0x")
        self.speed_combo.pack(side="left")

        # ── Panel nghe thử: nút test + ô câu test giãn nở ──
        test = self._panel(row=1, column=3, sticky="nsew")
        test.grid_columnconfigure(1, weight=1)
        self.test_btn = ctk.CTkButton(
            test, text="🔊 Test", height=32, width=76,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._on_test_voice,
        )
        self.test_btn.grid(row=0, column=0, sticky="w")
        self.test_entry = ctk.CTkEntry(
            test, height=32, corner_radius=6,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            placeholder_text="Nhập câu test, Enter để lưu...",
        )
        self.test_entry.insert(0, load_test_text())
        self.test_entry.grid(row=0, column=1, padx=(6, 0), sticky="ew")
        self.test_entry.bind("<Return>", lambda _: self._save_test_text())

        # KHÔNG render nút Ghép nhạc (SHOW_MERGE = False)

        # ── Panel hành động cuối cùng: chiếm dọc 2 hàng đầu ──
        actions = self._panel(row=0, column=4, rowspan=2)
        self.convert_btn = ctk.CTkButton(
            actions, text="⚡  Chuyển đổi", height=40, width=150, fg_color=theme.SUCCESS,
            hover_color=theme.SUCCESS_HOVER, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_convert,
        )
        self.convert_btn.pack(fill="x", pady=(0, 6))
        self.export_btn = ctk.CTkButton(
            actions, text="💾  Xuất file", height=32, width=150,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_export,
        )
        self.export_btn.pack(fill="x")
        self.stop_btn = ctk.CTkButton(
            actions, text="⏹  Dừng", height=32, width=150,
            fg_color=theme.ERROR, hover_color="#b91c1c", corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_stop,
        )
        # Chỉ hiện nút Dừng khi đang bận (xem set_busy)

        # ── Hàng 3: dòng thông báo riêng full-width ──
        self.status_label = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.status_label.grid(row=2, column=1, columnspan=4,
                               padx=6, pady=(0, 6), sticky="ew")

    # ── helpers ──

    def _set_logo(self, h: int) -> None:
        """Gán ảnh logo theo chiều cao cho trước (giữ tỉ lệ, giới hạn rộng)."""
        if self._logo_pil is None or h < 16:
            return
        w = max(1, int(self._logo_pil.width * h / self._logo_pil.height))
        w = min(w, 260)
        self._logo_h = h
        self._logo_img = ctk.CTkImage(self._logo_pil, size=(w, h))
        self._logo_label.configure(image=self._logo_img)

    def _fit_logo(self, event=None) -> None:
        """Co logo vừa full chiều cao panel (giữ tỉ lệ, giới hạn rộng)."""
        if self._logo_pil is None:
            return
        try:
            if event is not None and getattr(event, "height", 0) > 1:
                base = event.height
            else:
                base = self._brand_outer.winfo_height()
        except Exception:
            return
        h = base - 28  # trừ padding panel + viền
        if h < 16 or abs(h - self._logo_h) < 3:
            return
        self._set_logo(h)

    def _panel(self, row: int, column: int, rowspan: int = 1,
               columnspan: int = 1, sticky: str = "nsew") -> ctk.CTkFrame:
        """Panel trắng có viền bo góc cho 1 nhóm chức năng."""
        outer = ctk.CTkFrame(
            self, fg_color=theme.SURFACE,
            border_width=1, border_color=theme.SIDEBAR_DIVIDER, corner_radius=10,
        )
        outer.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan,
                   padx=5, pady=(8, 4), sticky=sticky)
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8, pady=6)
        return inner

    # ── public API ──

    def set_source_name(self, name: str | None) -> None:
        """Hiện tên văn bản đang mở ở hàng nguồn. None = chưa mở file."""
        if name:
            self.source_label.configure(text=name, text_color=theme.TEXT)
        else:
            self.source_label.configure(text=_NO_FILE_TEXT, text_color=theme.TEXT_DIM)

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
        self.test_btn.configure(state=state)
        if busy:
            self.stop_btn.pack(fill="x", before=self.convert_btn)
        else:
            self.stop_btn.pack_forget()

    def set_status(self, message: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=message, text_color=color)

    def get_test_text(self) -> str | None:
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
