from __future__ import annotations

from datetime import date, datetime, timedelta

import customtkinter as ctk

from core.licensing import fingerprint, guard, shortcode, trial
from ui import theme
from ui.shell.page import Page
from ui.ui_kit import Badge, Button, Card, SectionTitle


class LicensePage(Page):
    """Trang Bản quyền: trạng thái, hạn dùng, mã máy, nhập mã mới."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="license", title="Bản quyền",
                         subtitle="Trạng thái kích hoạt và hạn sử dụng", **kwargs)

        self._machine = fingerprint.format_machine_code()

        Button(self.header.actions, text="🔄  Làm mới", variant="secondary",
               command=self.refresh).pack(side="left", padx=(0, theme.SPACE_SM))
        self.activate_btn = Button(self.header.actions, text="Nhập mã mới",
                                   variant="primary", command=self._activate)
        self.activate_btn.pack(side="left")

        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)

        card = Card(self.body, padding=theme.SPACE_LG)
        card.grid(row=0, column=0, sticky="ew")
        box = card.content
        box.grid_columnconfigure(1, weight=1)

        self._badge = Badge(box, text="—", tone="neutral")
        self._badge.grid(row=0, column=0, columnspan=2, pady=(0, theme.SPACE_MD),
                         sticky="w")

        self._values: dict[str, ctk.CTkLabel] = {}
        rows = (("kind", "Loại"), ("expiry", "Hạn dùng"), ("left", "Còn lại"))
        for index, (key, label) in enumerate(rows, start=1):
            ctk.CTkLabel(
                box, text=label, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                text_color=theme.TEXT_DIM,
            ).grid(row=index, column=0, padx=(0, theme.SPACE_XL),
                   pady=theme.SPACE_XS, sticky="w")
            value = ctk.CTkLabel(
                box, text="—", anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
                text_color=theme.TEXT,
            )
            value.grid(row=index, column=1, pady=theme.SPACE_XS, sticky="w")
            self._values[key] = value

        ctk.CTkFrame(box, height=1, fg_color=theme.BORDER).grid(
            row=4, column=0, columnspan=2, pady=theme.SPACE_MD, sticky="ew")

        ctk.CTkLabel(
            box, text="Mã máy", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        ).grid(row=5, column=0, padx=(0, theme.SPACE_XL), sticky="w")

        machine_row = ctk.CTkFrame(box, fg_color="transparent")
        machine_row.grid(row=5, column=1, sticky="w")
        self.machine_label = ctk.CTkLabel(
            machine_row, text=self._machine, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 2, "bold"),
            text_color=theme.TEXT,
        )
        self.machine_label.pack(side="left")
        Button(machine_row, text="Sao chép", variant="secondary", size="sm",
               command=self._copy_machine).pack(side="left",
                                                padx=(theme.SPACE_SM, 0))

        self.note = ctk.CTkLabel(
            box, text="", anchor="w", justify="left", wraplength=760,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        )
        self.note.grid(row=6, column=0, columnspan=2,
                       pady=(theme.SPACE_MD, 0), sticky="w")

        help_card = Card(self.body, padding=theme.SPACE_LG)
        help_card.grid(row=1, column=0, sticky="nsew", pady=(theme.SPACE_MD, 0))
        help_box = help_card.content
        SectionTitle(help_box, "Cách kích hoạt").pack(anchor="w")
        ctk.CTkLabel(
            help_box,
            text=("1. Bấm “Sao chép” mã máy ở trên, gửi cho nhà phát triển.\n"
                  "2. Nhận mã kích hoạt 15 ký tự (hoặc file .lic).\n"
                  "3. Bấm “Nhập mã mới”, dán mã và xác nhận.\n\n"
                  "Máy chạy hoàn toàn offline — không cần mạng ở bất kỳ bước nào. "
                  "Đổi ổ cứng hoặc cài lại Windows sẽ cần mã mới."),
            anchor="w", justify="left", wraplength=760,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        ).pack(anchor="w", pady=(theme.SPACE_SM, 0))

        self._help_card = help_card
        self.refresh()
        # Khoá chiều cao tối thiểu: thiếu chỗ thì Page.body tự hiện thanh cuộn
        # thay vì bóp card hướng dẫn xuống còn vài chục px.
        self.after_idle(self._lock_help_height)

    def _lock_help_height(self) -> None:
        try:
            self._help_card.update_idletasks()
            self.body.grid_rowconfigure(
                1, minsize=self._help_card.winfo_reqheight())
        except Exception:
            pass

    # ── dữ liệu ──

    def refresh(self) -> None:
        status = guard.check_startup(use_cache=False)
        info = trial.info()

        if status.state == guard.LICENSED:
            self._badge.configure(text="Đã kích hoạt"); self._badge.set_tone("success")
        elif status.state == guard.TRIAL:
            self._badge.configure(text="Dùng thử"); self._badge.set_tone("info")
        elif status.state in (guard.EXPIRED, guard.TRIAL_EXPIRED):
            self._badge.configure(text="Hết hạn"); self._badge.set_tone("danger")
        else:
            self._badge.configure(text="Chưa kích hoạt"); self._badge.set_tone("danger")

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
                theme.WARNING if left <= 7 else theme.TEXT)
            self._values["left"].configure(text=f"{left} ngày",
                                           text_color=color)
        else:
            self._values["left"].configure(text="—", text_color=theme.TEXT)

        self.note.configure(text=status.message or "")
        self.activate_btn.configure(
            text="Nhập mã mới" if status.active else "Kích hoạt ngay")
        self.set_subtitle(f"Mã máy {self._machine} · "
                          f"{'đã kích hoạt' if status.active else 'chưa kích hoạt'}")

    # ── hành động ──

    def _copy_machine(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self._machine)
            self.note.configure(text="Đã sao chép mã máy.",
                                text_color=theme.SUCCESS)
        except Exception:
            self.note.configure(text="Không sao chép được.",
                                text_color=theme.ERROR)

    def _activate(self) -> None:
        self.ctx._open_activation()
        self.refresh()
        self.ctx._refresh_license_badge()

    def on_show(self) -> None:
        self.refresh()
