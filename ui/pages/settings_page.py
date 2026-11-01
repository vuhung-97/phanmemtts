from __future__ import annotations

import customtkinter as ctk

from engine import setup_tools
from ui import theme
from ui.shell.page import Page
from ui.ui_kit import Badge, Button, Card, Field
from ui.config import save_settings

PRECISION_VALUES = ["fp32", "int8"]
THREAD_VALUES = [0, 2, 4, 6, 8]
STORAGE_VALUES = ["auto", "memory", "disk"]

PRECISION_LABELS = {
    "fp32": "FP32 — chất lượng cao (mặc định)",
    "int8": "INT8 — nhanh hơn ~20–30%, nhỏ hơn ~3× (cần CPU có VNNI)",
}
THREAD_LABELS = {
    0: "Tự động (theo CPU)",
    2: "2 luồng",
    4: "4 luồng",
    6: "6 luồng",
    8: "8 luồng",
}
STORAGE_LABELS = {
    "auto": "Tự động (RAM cho bài ngắn, đĩa cho bài dài)",
    "memory": "Luôn trong RAM (nhanh nhất, bài dài sẽ tốn bộ nhớ)",
    "disk": "Luôn ghi file tạm (bài dài không tốn RAM)",
}


def _combo(parent, values: list[str], width: int = 320) -> ctk.CTkComboBox:
    return ctk.CTkComboBox(
        parent, values=values, height=34, width=width, state="readonly",
        corner_radius=theme.RADIUS_SM,
        fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
        border_color=theme.BORDER, border_width=1,
        button_color=theme.SURFACE_2, button_hover_color=theme.HOVER_BG,
        dropdown_fg_color=theme.SURFACE, dropdown_text_color=theme.TEXT,
        font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
    )


class SettingsPage(Page):
    """Trang Cài đặt: độ chính xác model, số luồng CPU, cách lưu audio."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="settings", title="Cài đặt",
                         subtitle="Cấu hình model và cách lưu âm thanh", **kwargs)

        self._dirty = False
        self.save_btn = Button(self.header.actions, text="Lưu",
                               variant="primary", command=self._save)
        self.save_btn.pack(side="left")
        self._badge = Badge(self.header.actions, text="", tone="warning")

        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=0)
        self.body.grid_rowconfigure(2, weight=1)

        card = Card(self.body, padding=theme.SPACE_LG)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        row = 0
        row = self._section(card, "Mô hình", row)
        self.precision_combo = _combo(card, list(PRECISION_LABELS.values()))
        row = self._row(card, row, "Độ chính xác", self.precision_combo)
        self.int8_label = ctk.CTkLabel(
            card, text="", text_color=theme.TEXT_DIM, anchor="w",
            justify="left", wraplength=620,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.int8_label.grid(row=row, column=1, pady=(0, theme.SPACE_SM),
                             sticky="w")
        row += 1

        row = self._section(card, "Hiệu năng", row)
        self.threads_combo = _combo(card, list(THREAD_LABELS.values()), 200)
        row = self._row(card, row, "Số luồng CPU", self.threads_combo)
        ctk.CTkLabel(
            card, text="Chạy hoàn toàn trên CPU của máy (bản phát hành không kèm GPU).",
            text_color=theme.TEXT_DIM, justify="left", wraplength=620,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        ).grid(row=row, column=1, pady=(0, theme.SPACE_SM), sticky="w")
        row += 1

        row = self._section(card, "Cách lưu âm thanh", row)
        self.storage_combo = _combo(card, list(STORAGE_LABELS.values()), 420)
        row = self._row(card, row, "Bộ nhớ", self.storage_combo)

        note = Card(self.body, padding=theme.SPACE_MD)
        note.grid(row=1, column=0, sticky="ew", pady=(theme.SPACE_MD, 0))
        ctk.CTkLabel(
            note, text="Thay đổi độ chính xác hoặc số luồng sẽ nạp lại model "
                       "ở lần chuyển đổi tiếp theo.",
            text_color=theme.TEXT_DIM, anchor="w", justify="left",
            wraplength=720,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        ).pack(anchor="w")
        self.status_label = ctk.CTkLabel(
            note, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.status_label.pack(anchor="w", pady=(theme.SPACE_XS, 0))

        for combo in (self.precision_combo, self.threads_combo,
                      self.storage_combo):
            combo.configure(command=lambda _v: self._mark_dirty())

        self._load_from_settings()

    # ── layout helper ──

    def _section(self, parent, text: str, row: int) -> int:
        ctk.CTkLabel(
            parent, text=text, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).grid(row=row, column=0, columnspan=2,
               pady=(theme.SPACE_MD, theme.SPACE_XS), sticky="w")
        return row + 1

    def _row(self, parent, row: int, label: str, widget) -> int:
        ctk.CTkLabel(
            parent, text=label, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        ).grid(row=row, column=0, padx=(0, theme.SPACE_MD),
               pady=theme.SPACE_XS, sticky="w")
        widget.grid(row=row, column=1, pady=theme.SPACE_XS, sticky="w")
        return row + 1

    # ── dữ liệu ──

    def _load_from_settings(self) -> None:
        settings = getattr(self.ctx, "_settings", {}) or {}
        self.precision_combo.set(PRECISION_LABELS.get(
            settings.get("precision", "fp32"), PRECISION_LABELS["fp32"]))
        self.threads_combo.set(THREAD_LABELS.get(
            int(settings.get("threads", 0) or 0), THREAD_LABELS[0]))
        self.storage_combo.set(STORAGE_LABELS.get(
            settings.get("storage", "auto"), STORAGE_LABELS["auto"]))
        self._dirty = False
        self._refresh_int8()
        self._update_badge()

    def _collect(self) -> dict:
        precision = next((k for k, v in PRECISION_LABELS.items()
                          if v == self.precision_combo.get()), "fp32")
        threads = next((k for k, v in THREAD_LABELS.items()
                        if v == self.threads_combo.get()), 0)
        storage = next((k for k, v in STORAGE_LABELS.items()
                        if v == self.storage_combo.get()), "auto")
        return {"precision": precision, "threads": threads, "storage": storage}

    def _refresh_int8(self) -> None:
        try:
            installed = setup_tools.int8_installed()
        except Exception:
            installed = False
        try:
            advice = setup_tools.int8_recommendation()
        except Exception:
            advice = ""
        want_int8 = self._collect()["precision"] == "int8"
        if installed:
            prefix = "✔ Model INT8 có sẵn trong bản cài."
            color = theme.SUCCESS if want_int8 else theme.TEXT_DIM
        elif want_int8:
            prefix = ("⚠ Bản cài thiếu model INT8 (thư mục onnx_int8) — hãy chép "
                      "lại thư mục 'models/' hoặc chọn FP32.")
            color = theme.ERROR
        else:
            prefix = "⚠ Bản cài không có model INT8 — chỉ dùng được FP32."
            color = theme.TEXT_DIM
        self.int8_label.configure(text=f"{prefix} {advice}".strip(),
                                  text_color=color)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._refresh_int8()
        self._update_badge()
        self.status_label.configure(text="Có thay đổi chưa lưu.",
                                    text_color=theme.WARNING)

    def _update_badge(self) -> None:
        if self._dirty:
            self._badge.configure(text="Chưa lưu"); self._badge.set_tone("warning")
            if not self._badge.winfo_ismapped():
                self._badge.pack(side="left", padx=(0, theme.SPACE_SM),
                                 before=self.save_btn)
        elif self._badge.winfo_ismapped():
            self._badge.pack_forget()

    def _save(self) -> None:
        data = self._collect()
        previous = dict(getattr(self.ctx, "_settings", {}) or {})
        changed = (data["precision"] != previous.get("precision")
                   or int(data["threads"]) != int(previous.get("threads", 0)))
        self.ctx._settings.update(data)
        save_settings(self.ctx._settings)
        if changed:
            self.ctx._model_manager.set_runtime(
                precision=data["precision"], threads=data["threads"])
        self._dirty = False
        self._update_badge()
        self.ctx.shell.status("Đã lưu cài đặt.", theme.SUCCESS)
        self.status_label.configure(
            text="Đã lưu." + (" Model sẽ nạp lại ở lần chuyển đổi sau."
                              if changed else ""),
            text_color=theme.SUCCESS,
        )

    # ── vòng đời ──

    def on_show(self) -> None:
        self._load_from_settings()
        self.status_label.configure(text="")

    def on_hide(self) -> None:
        if self._dirty:
            self.ctx.shell.status("Cài đặt có thay đổi chưa lưu.", theme.WARNING)
