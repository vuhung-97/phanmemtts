from __future__ import annotations

from tkinter import Menu
from typing import Callable

import customtkinter as ctk
from PIL import Image

from core.paths import resource_path
from ui import theme
from ui.config import load_test_text, save_test_text

_LOGO_PATH = resource_path("logo/logo.jpg")

# Mở lại chức năng ghép nhạc (nay nằm trong menu Công cụ).
SHOW_MERGE = True

_NO_FILE_TEXT = "(chưa mở văn bản)"


class TopBar(ctk.CTkFrame):
    """Header 4 hàng kiểu ứng dụng Windows:

    Hàng 0: menu bar (Tệp / Công cụ / Trợ giúp).
    Hàng 1: logo | nguồn văn bản (Mở file + tên file) | Chuyển đổi / Xuất file.
    Hàng 2: giọng đọc + tốc độ | nghe thử.
    Hàng 3: dòng thông báo full-width.
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
        on_merge: Callable[[], None] | None = None,  # mở từ menu Công cụ
        on_batch: Callable[[], None] | None = None,
        on_settings: Callable[[], None] | None = None,
        on_history: Callable[[], None] | None = None,
        on_help: Callable[[], None] | None = None,
        on_about: Callable[[], None] | None = None,
        on_license: Callable[[], None] | None = None,
        on_dictionary: Callable[[], None] | None = None,
        on_clean: Callable[[], None] | None = None,
        on_terms: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
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
        self._on_batch = on_batch
        self._on_settings = on_settings
        self._on_history = on_history
        self._on_help = on_help
        self._on_about = on_about
        self._on_license = on_license
        self._on_dictionary = on_dictionary
        self._on_clean = on_clean
        self._on_terms = on_terms
        self._on_close = on_close

        # Chỉ số mục menu cần khoá khi đang chuyển đổi (None = không có mục đó).
        self._merge_index: int | None = None
        self._batch_index: int | None = None
        self._settings_index: int | None = None
        self._history_index: int | None = None

        # Dải menu trên cùng + vùng panel bên dưới. Tách 2 packer để thanh menu
        # không kéo giãn cột của lưới bên dưới (giữ nguyên chiều ngang ô test).
        self._menubar = ctk.CTkFrame(self, fg_color=theme.SIDEBAR_BG, height=30)
        self._menubar.pack(side="top", fill="x")
        self._menubar.pack_propagate(False)
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(side="top", fill="both", expand=True)

        # Cột 3 (panel nghe thử) giãn nở theo chiều ngang
        self._body.grid_columnconfigure(3, weight=1)

        # ── Menu bar kiểu Windows ──
        self._build_menubar()

        self._build_body()

    # ── Menu bar kiểu Windows ──

    def _make_menu(self) -> Menu:
        """Menu popup gốc của Tk (có phím tắt, dấu phân cách, trạng thái mờ)."""
        return Menu(
            self, tearoff=0, bd=0, relief="flat",
            bg=theme.SURFACE, fg=theme.TEXT,
            activebackground=theme.ACCENT, activeforeground="#ffffff",
            disabledforeground=theme.TIMELINE_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )

    def _build_menubar(self) -> None:
        """Dải trên cùng: Tệp / Công cụ / Trợ giúp + phím tắt."""
        bar = ctk.CTkFrame(self._menubar, fg_color="transparent")
        bar.pack(side="left", fill="y", padx=(10, 0))
        self.menubar = self._menubar
        self._menubar_buttons: dict[str, ctk.CTkButton] = {}
        self.menus: dict[str, Menu] = {}

        for key, label in (("file", "Tệp"), ("tools", "Công cụ"), ("help", "Trợ giúp")):
            button = ctk.CTkButton(
                bar, text=label, width=0, height=24, corner_radius=4,
                fg_color="transparent", hover_color=theme.HOVER_BG,
                text_color=theme.TEXT,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                command=lambda k=key: self._popup_menu(k),
            )
            button.pack(side="left", padx=(0, 2), pady=3)
            self._menubar_buttons[key] = button

        # ── Tệp ──
        file_menu = self._make_menu()
        file_menu.add_command(label="Mở văn bản…", accelerator="Ctrl+O",
                              command=self._on_open_file)
        file_menu.add_separator()
        close = self._on_close or self.winfo_toplevel().destroy
        file_menu.add_command(label="Thoát", accelerator="Alt+F4", command=close)
        self.menus["file"] = file_menu

        # ── Công cụ: Ghép nhạc / Hàng loạt / Lịch sử / Từ điển / Làm sạch / Cài đặt ──
        tools_menu = self._make_menu()
        if SHOW_MERGE and self._on_merge is not None:
            tools_menu.add_command(label="Ghép nhạc", command=self._on_merge)
            self._merge_index = tools_menu.index("end")
        if self._on_batch is not None:
            tools_menu.add_command(label="Chuyển đổi hàng loạt…",
                                   accelerator="Ctrl+B",
                                   command=self._on_batch)
            self._batch_index = tools_menu.index("end")
        if self._on_history is not None:
            tools_menu.add_command(label="Lịch sử bản dựng", accelerator="Ctrl+H",
                                   command=self._on_history)
            self._history_index = tools_menu.index("end")
        if self._on_dictionary is not None or self._on_clean is not None:
            if tools_menu.index("end") is not None:
                tools_menu.add_separator()
            if self._on_dictionary is not None:
                tools_menu.add_command(
                    label="Từ điển phát âm…", accelerator="Ctrl+Shift+D",
                    command=self._on_dictionary)
            if self._on_clean is not None:
                tools_menu.add_command(
                    label="Làm sạch văn bản", accelerator="Ctrl+Shift+K",
                    command=self._on_clean)
        if self._on_settings is not None:
            if tools_menu.index("end") is not None:
                tools_menu.add_separator()
            tools_menu.add_command(label="Cài đặt", command=self._on_settings)
            self._settings_index = tools_menu.index("end")
        self.menus["tools"] = tools_menu
        if tools_menu.index("end") is None:
            self._menubar_buttons["tools"].pack_forget()

        # ── Trợ giúp ──
        help_menu = self._make_menu()
        if self._on_license is not None:
            help_menu.add_command(label="Thông tin bản quyền",
                                  accelerator="Ctrl+Shift+L",
                                  command=self._on_license)
            help_menu.add_separator()
        if self._on_help is not None:
            help_menu.add_command(label="Hướng dẫn sử dụng", command=self._on_help)
        if self._on_terms is not None:
            help_menu.add_command(label="Điều khoản sử dụng",
                                  command=self._on_terms)
        if self._on_about is not None:
            help_menu.add_command(label="Giới thiệu", command=self._on_about)
        self.menus["help"] = help_menu
        if help_menu.index("end") is None:
            self._menubar_buttons["help"].pack_forget()

        # ── Nhãn trạng thái bản quyền (bên phải thanh menu) ──
        self.license_label = ctk.CTkLabel(
            self._menubar, text="", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), cursor="hand2",
        )
        self.license_label.pack(side="right", padx=(0, 12))
        if self._on_license is not None:
            self.license_label.bind("<Button-1>",
                                    lambda _e: self._on_license())

        # ── Phím tắt (chuẩn Windows) ──
        top = self.winfo_toplevel()
        top.bind("<Control-o>", lambda _e: self._on_open_file())
        if self._on_history is not None:
            top.bind("<Control-h>", lambda _e: self._on_history())
        if self._on_license is not None:
            top.bind("<Control-Shift-L>", lambda _e: self._on_license())
            top.bind("<Control-Shift-l>", lambda _e: self._on_license())
        if self._on_dictionary is not None:
            top.bind("<Control-Shift-D>", lambda _e: self._on_dictionary())
            top.bind("<Control-Shift-d>", lambda _e: self._on_dictionary())
        if self._on_clean is not None:
            top.bind("<Control-Shift-K>", lambda _e: self._on_clean())
            top.bind("<Control-Shift-k>", lambda _e: self._on_clean())
        if self._on_batch is not None:
            top.bind("<Control-b>", lambda _e: self._on_batch())
        top.bind("<Alt-f>", lambda _e: self._open_menu_by_key("file"))
        top.bind("<Alt-c>", lambda _e: self._open_menu_by_key("tools"))
        top.bind("<Alt-t>", lambda _e: self._open_menu_by_key("help"))

    def _popup_menu(self, key: str) -> None:
        """Mở menu ngay dưới nút tương ứng."""
        menu = self.menus.get(key)
        button = self._menubar_buttons.get(key)
        if menu is None or button is None:
            return
        try:
            menu.tk_popup(button.winfo_rootx(),
                          button.winfo_rooty() + button.winfo_height())
        finally:
            menu.grab_release()

    def _open_menu_by_key(self, key: str) -> None:
        if key in self._menubar_buttons:
            self.after(1, lambda: self._popup_menu(key))

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

    def _build_body(self) -> None:
        """Dựng logo + 3 hàng nội dung + dòng trạng thái.

        Tách khỏi __init__ để code object của __init__ không vượt
        giới hạn 32 KB của PyArmor bản miễn phí.
        """

        # ── Panel thương hiệu: logo full chiều cao 3 hàng ──
        self._brand_outer = ctk.CTkFrame(
            self._body, fg_color=theme.SURFACE,
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

        # ── Hàng 0: nguồn văn bản (Mở file + tên file) ──
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
        self.source_label.grid(row=0, column=1, padx=(8, 8), sticky="ew")

        # ── Panel giọng đọc: combo + thêm + tốc độ ──
        voice = self._panel(row=1, column=1, columnspan=2, sticky="w")
        ctk.CTkLabel(
            voice, text="Giọng đọc", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1, "bold"),
        ).pack(side="left", padx=(0, 4))
        self.voice_combo = ctk.CTkComboBox(
            voice, height=32, width=200, state="readonly", values=["(chưa có model)"],
            command=self._voice_changed, corner_radius=6,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            button_color=theme.BUTTON_HOVER, button_hover_color=theme.ACCENT,
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
            voice, height=32, width=80, state="readonly",
            values=["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x"],
            command=self._speed_changed, corner_radius=6,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            button_color=theme.BUTTON_HOVER, button_hover_color=theme.ACCENT,
            dropdown_fg_color=theme.INPUT_BG,
            dropdown_text_color=theme.INPUT_TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.speed_combo.set("1.0x")
        self.speed_combo.pack(side="left")

        # ── Panel nghe thử: nút test + ô câu test giãn nở ──
        # sticky="ew" (KHÔNG "nsew"): panel giữ đúng chiều cao như panel giọng
        # đọc bên trái -> các ô cùng hàng không bị lệch dòng.
        test = self._panel(row=1, column=3, sticky="ew")
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

        # ── Panel phải (hàng 1-2): 2 nút hành động chính ──
        # Chiều cao khả dụng ≈ 112px -> chia 3:2 (Chuyển đổi là nút chính).
        actions = self._panel(row=0, column=4, rowspan=2)
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_rowconfigure(0, weight=3)
        actions.grid_rowconfigure(1, weight=2)

        self.convert_btn = ctk.CTkButton(
            actions, text="⚡  Chuyển đổi", height=40, width=150,
            fg_color=theme.SUCCESS, hover_color=theme.SUCCESS_HOVER,
            corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 1, "bold"),
            command=self._on_convert,
        )
        self.convert_btn.grid(row=0, column=0, pady=(0, 6), sticky="nsew")

        self.export_btn = ctk.CTkButton(
            actions, text="💾  Xuất file", height=36, width=150,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._on_export,
        )
        self.export_btn.grid(row=1, column=0, sticky="nsew")
        # Không dùng nút Dừng riêng: khi bận, convert_btn biến thành nút Dừng.

        # ── Hàng 2: dòng thông báo riêng full-width ──
        self.status_label = ctk.CTkLabel(
            self._body, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.status_label.grid(row=2, column=1, columnspan=4,
                               padx=6, pady=(0, 6), sticky="ew")


    def _panel(self, row: int, column: int, rowspan: int = 1,
               columnspan: int = 1, sticky: str = "nsew") -> ctk.CTkFrame:
        """Panel trắng có viền bo góc cho 1 nhóm chức năng."""
        outer = ctk.CTkFrame(
            self._body, fg_color=theme.SURFACE,
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
        # Khi bận: convert_btn biến thành nút Dừng tại chỗ (không thêm nút mới).
        state = "disabled" if busy else "normal"
        self.export_btn.configure(state=state)
        self.test_btn.configure(state=state)
        # Khoá Ghép nhạc + Cài đặt trong menu (đổi precision giữa lúc chuyển đổi
        # sẽ nạp lại model); Lịch sử vẫn mở được vì chỉ đọc.
        tools = self.menus.get("tools")
        if tools is not None:
            for index in (self._merge_index, self._batch_index,
                          self._settings_index):
                if index is not None:
                    tools.entryconfigure(index, state=state)
        if busy:
            self.convert_btn.configure(
                text="⏹  Dừng", fg_color=theme.ERROR, hover_color="#b91c1c",
                command=self._on_stop, state="normal",
            )
        else:
            self.convert_btn.configure(
                text="⚡  Chuyển đổi", fg_color=theme.SUCCESS,
                hover_color=theme.SUCCESS_HOVER, command=self._on_convert,
                state="normal",
            )

    def set_status(self, message: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=message, text_color=color)

    def set_license(self, text: str, color: str = theme.TEXT_DIM) -> None:
        """Nhãn bản quyền bên phải thanh menu (🔑 Còn N ngày / Vĩnh viễn…)."""
        self.license_label.configure(text=text, text_color=color)

    def set_export_locked(self, locked: bool) -> None:
        """Đổi nhãn nút Xuất file khi chưa kích hoạt (vẫn bấm được để mở hộp thoại)."""
        self.export_btn.configure(
            text="🔒  Xuất file" if locked else "💾  Xuất file")

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
