"""Hộp thoại Thông tin bản quyền (Trợ giúp → Thông tin bản quyền)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import customtkinter as ctk

from core.licensing import fingerprint, guard, shortcode, trial
from ui import theme
from ui.components.activation_dialog import ask_activation


class LicenseDialog(ctk.CTkToplevel):
    """Hiện loại key, hạn dùng, số ngày còn lại và mã máy."""

    def __init__(self, master, on_activate=None) -> None:
        super().__init__(master)
        self.title("Thông tin bản quyền")
        self.geometry("580x430")
        self.resizable(False, False)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._on_activate = on_activate
        self._machine = fingerprint.format_machine_code()
        self._build()
        self._refresh()

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _: self.destroy())

    # ── UI ──

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Thông tin bản quyền",
            font=(theme.FONT_FAMILY, theme.TITLE_SIZE + 3, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=24, pady=(20, 10), sticky="w")

        body = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=10,
                            border_width=1, border_color=theme.SIDEBAR_DIVIDER)
        body.grid(row=1, column=0, padx=24, sticky="ew")
        body.grid_columnconfigure(1, weight=1)

        self._values: dict[str, ctk.CTkLabel] = {}
        rows = [
            ("state", "Trạng thái"),
            ("kind", "Loại"),
            ("expiry", "Hạn dùng"),
            ("left", "Còn lại"),
        ]
        for i, (key, label) in enumerate(rows):
            ctk.CTkLabel(
                body, text=label, text_color=theme.TEXT_DIM, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            ).grid(row=i, column=0, padx=(16, 8), pady=6, sticky="w")
            value = ctk.CTkLabel(
                body, text="—", text_color=theme.TEXT, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            )
            value.grid(row=i, column=1, padx=(0, 16), pady=6, sticky="w")
            self._values[key] = value

        ctk.CTkLabel(
            body, text="Mã máy", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        ).grid(row=4, column=0, padx=(16, 8), pady=(6, 14), sticky="w")

        may = ctk.CTkFrame(body, fg_color="transparent")
        may.grid(row=4, column=1, padx=(0, 16), pady=(6, 14), sticky="ew")
        may.grid_columnconfigure(0, weight=1)

        self.machine_label = ctk.CTkLabel(
            may, text=self._machine, text_color=theme.TEXT, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 2, "bold"),
        )
        self.machine_label.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            may, text="Sao chép", width=90, height=28,
            fg_color=theme.BUTTON_BG, hover_color=theme.BUTTON_HOVER,
            text_color=theme.TEXT, border_width=1,
            border_color=theme.SIDEBAR_DIVIDER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=self._copy_machine,
        ).grid(row=0, column=1, padx=(8, 0))

        self.note = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), wraplength=520,
        )
        self.note.grid(row=2, column=0, padx=24, pady=(10, 0), sticky="w")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=24, pady=(16, 16), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self.activate_btn = ctk.CTkButton(
            bottom, text="Nhập mã mới", width=150, height=36,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._activate_new,
        )
        self.activate_btn.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            bottom, text="Đóng", width=120, height=36,
            fg_color=theme.DARK_BUTTON_BG, hover_color=theme.DARK_BUTTON_HOVER,
            text_color=theme.DARK_BUTTON_TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self.destroy,
        ).grid(row=0, column=1, sticky="e")

    # ── Dữ liệu ──

    def _refresh(self) -> None:
        status = guard.check_startup(use_cache=False)
        info = trial.info()
        today = date.today()

        if status.state == guard.LICENSED:
            state_text, color = "Đã kích hoạt", theme.SUCCESS
        elif status.state == guard.TRIAL:
            state_text, color = "Dùng thử", theme.SUCCESS
        elif status.state in (guard.EXPIRED, guard.TRIAL_EXPIRED):
            state_text, color = "Hết hạn", theme.ERROR
        else:
            state_text, color = "Chưa kích hoạt", theme.ERROR
        self._values["state"].configure(text=state_text, text_color=color)

        if status.kind is not None:
            self._values["kind"].configure(text=shortcode.KIND_LABELS.get(
                status.kind, "—"))
        elif info.started:
            self._values["kind"].configure(text="Dùng thử 7 ngày")
        else:
            self._values["kind"].configure(text="—")

        if status.expiry is not None:
            self._values["expiry"].configure(
                text=status.expiry.strftime("%d/%m/%Y"))
        elif status.is_lifetime:
            self._values["expiry"].configure(text="Không giới hạn")
        elif info.started and info.start_ts:
            end = datetime.fromtimestamp(info.start_ts, tz=None).date() \
                + timedelta(days=trial.TRIAL_DAYS)
            self._values["expiry"].configure(text=end.strftime("%d/%m/%Y"))
        else:
            self._values["expiry"].configure(text="—")

        if status.is_lifetime:
            self._values["left"].configure(text="Không giới hạn",
                                           text_color=theme.TEXT)
        elif status.days_left is not None:
            left = max(0, int(status.days_left))
            color = theme.ERROR if left <= 1 else (
                "#b7791f" if left <= 7 else theme.TEXT)
            self._values["left"].configure(text=f"{left} ngày", text_color=color)
        else:
            self._values["left"].configure(text="—", text_color=theme.TEXT)

        self.note.configure(text=status.message if status.message else "")
        self.activate_btn.configure(
            text="Nhập mã mới" if status.active else "Kích hoạt ngay")

    def _copy_machine(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self._machine)
            self.note.configure(text="Đã sao chép mã máy.",
                                text_color=theme.SUCCESS)
        except Exception:
            self.note.configure(text="Không sao chép được.",
                                text_color=theme.ERROR)

    def _activate_new(self) -> None:
        if self._on_activate is not None:
            self._on_activate()
        else:
            ask_activation(self)
        self._refresh()
