from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from engine import setup_tools
from ui import theme

PRECISION_VALUES = ["fp32", "int8"]
THREAD_VALUES = [0, 2, 4, 6, 8]
STORAGE_VALUES = ["auto", "memory", "disk"]

PRECISION_LABELS = {
    "fp32": "FP32 — chất lượng cao (mặc định)",
    "int8": "INT8 — nhanh hơn ~1.6×, nhỏ ~4× (cần CPU có VNNI)",
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


class SettingsDialog(ctk.CTkToplevel):
    """Dialog cài đặt: độ chính xác model, số luồng, GPU, cách lưu audio."""

    def __init__(self, master, settings: dict,
                 on_save: Callable[[dict], None]) -> None:
        super().__init__(master)
        self.title("Cài đặt")
        self.geometry("560x640")
        self.minsize(520, 560)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._settings = dict(settings)
        self._on_save = on_save
        self._busy = False

        self._build_ui()
        self._refresh_status()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _: self._cancel())

    # ── UI ──

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="⚙  Cài đặt",
            font=(theme.FONT_FAMILY, theme.TITLE_SIZE + 2, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=20, sticky="ew")
        body.grid_columnconfigure(1, weight=1)

        # ── Mô hình ──
        self._section(body, "Mô hình", 0)

        ctk.CTkLabel(body, text="Độ chính xác", text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                     ).grid(row=1, column=0, padx=(0, 10), pady=6, sticky="w")
        self.precision_combo = ctk.CTkComboBox(
            body, values=list(PRECISION_LABELS.values()), height=32,
            state="readonly", corner_radius=6, font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            button_color=theme.BUTTON_HOVER, button_hover_color=theme.ACCENT,
            dropdown_fg_color=theme.INPUT_BG, dropdown_text_color=theme.INPUT_TEXT,
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.precision_combo.grid(row=1, column=1, pady=6, sticky="ew")
        self._sync_precision()

        self.int8_label = ctk.CTkLabel(
            body, text="", text_color=theme.TEXT_DIM, wraplength=480,
            justify="left", font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.int8_label.grid(row=2, column=0, columnspan=2, pady=(2, 4), sticky="w")

        self.int8_btn = ctk.CTkButton(
            body, text="⬇  Tải model INT8", height=30, width=170,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._download_int8,
        )
        self.int8_btn.grid(row=3, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # ── Hiệu năng ──
        self._section(body, "Hiệu năng", 4)

        ctk.CTkLabel(body, text="Số luồng CPU", text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                     ).grid(row=5, column=0, padx=(0, 10), pady=6, sticky="w")
        self.threads_combo = ctk.CTkComboBox(
            body, values=list(THREAD_LABELS.values()), height=32, width=160,
            state="readonly", corner_radius=6, font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            button_color=theme.BUTTON_HOVER, button_hover_color=theme.ACCENT,
            dropdown_fg_color=theme.INPUT_BG, dropdown_text_color=theme.INPUT_TEXT,
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.threads_combo.grid(row=5, column=1, pady=6, sticky="w")
        self._sync_threads()

        self.gpu_label = ctk.CTkLabel(
            body, text="", text_color=theme.TEXT_DIM, wraplength=480,
            justify="left", font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.gpu_label.grid(row=6, column=0, columnspan=2, pady=(2, 4), sticky="w")

        self.gpu_btn = ctk.CTkButton(
            body, text="⚡  Cài hỗ trợ GPU", height=30, width=170,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._install_gpu,
        )
        self.gpu_btn.grid(row=7, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # ── Lưu trữ ──
        self._section(body, "Cách lưu âm thanh", 8)

        ctk.CTkLabel(body, text="Bộ nhớ", text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                     ).grid(row=9, column=0, padx=(0, 10), pady=6, sticky="w")
        self.storage_combo = ctk.CTkComboBox(
            body, values=list(STORAGE_LABELS.values()), height=32, width=300,
            state="readonly", corner_radius=6, font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            button_color=theme.BUTTON_HOVER, button_hover_color=theme.ACCENT,
            dropdown_fg_color=theme.INPUT_BG, dropdown_text_color=theme.INPUT_TEXT,
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.storage_combo.grid(row=9, column=1, pady=6, sticky="ew")
        self._sync_storage()

        # ── Trạng thái ──
        self.status_label = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM, wraplength=500,
            justify="left", font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.status_label.grid(row=2, column=0, padx=20, pady=(10, 4), sticky="w")

        # ── Nút ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=20, pady=(6, 16), sticky="ew")
        bottom.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            bottom, text="💾 Lưu", height=36, fg_color=theme.DARK_BUTTON_BG,
            hover_color=theme.DARK_BUTTON_HOVER, text_color=theme.DARK_BUTTON_TEXT,
            corner_radius=8, font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._save,
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            bottom, text="✕ Huỷ", height=36, fg_color="transparent",
            border_width=1, border_color=theme.SIDEBAR_DIVIDER, text_color=theme.TEXT,
            hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), command=self._cancel,
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _section(self, parent, text: str, row: int) -> None:
        ctk.CTkLabel(
            parent, text=text, font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).grid(row=row, column=0, columnspan=2, pady=(10, 2), sticky="w")

    # ── Đồng bộ combobox ↔ settings ──

    def _sync_precision(self) -> None:
        value = self._settings.get("precision", "fp32")
        self.precision_combo.set(PRECISION_LABELS.get(value, PRECISION_LABELS["fp32"]))

    def _sync_threads(self) -> None:
        value = int(self._settings.get("threads", 0) or 0)
        self.threads_combo.set(THREAD_LABELS.get(value, THREAD_LABELS[0]))

    def _sync_storage(self) -> None:
        value = self._settings.get("storage", "auto")
        self.storage_combo.set(STORAGE_LABELS.get(value, STORAGE_LABELS["auto"]))

    def _collect(self) -> dict:
        precision = "fp32"
        for key, label in PRECISION_LABELS.items():
            if self.precision_combo.get() == label:
                precision = key
        threads = 0
        for key, label in THREAD_LABELS.items():
            if self.threads_combo.get() == label:
                threads = key
        storage = "auto"
        for key, label in STORAGE_LABELS.items():
            if self.storage_combo.get() == label:
                storage = key
        return {
            "precision": precision,
            "threads": threads,
            "storage": storage,
            "gpu": bool(self._settings.get("gpu", False)),
        }

    # ── Trạng thái ──

    def _refresh_status(self) -> None:
        try:
            installed = setup_tools.int8_installed()
        except Exception:
            installed = False
        try:
            advice = setup_tools.int8_recommendation()
        except Exception:
            advice = ""
        if installed:
            self.int8_label.configure(
                text=f"✔ Đã có model INT8 trên máy. {advice}", text_color=theme.SUCCESS)
            self.int8_btn.configure(state="disabled", text="✔ Đã tải INT8")
        else:
            self.int8_label.configure(
                text=f"Chưa có model INT8. {advice}", text_color=theme.TEXT_DIM)
            self.int8_btn.configure(state="normal", text="⬇  Tải model INT8")

        try:
            gpu_ok, gpu_msg = setup_tools.gpu_status()
        except Exception:
            gpu_ok, gpu_msg = False, ""
        self.gpu_label.configure(
            text=gpu_msg,
            text_color=theme.SUCCESS if gpu_ok else theme.TEXT_DIM,
        )
        self.gpu_btn.configure(state="disabled" if gpu_ok else "normal")

    # ── Hành động ──

    def _download_int8(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.int8_btn.configure(state="disabled", text="Đang tải...")
        self._set_status("Đang tải model INT8 (~150 MB)...", theme.TEXT_DIM)

        def worker() -> None:
            try:
                setup_tools.download_int8(self._set_status)
                self.after(0, self._int8_done)
            except Exception as exc:
                self.after(0, lambda: self._int8_failed(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _int8_done(self) -> None:
        self._busy = False
        self._set_status("Đã tải model INT8. Chọn INT8 ở trên để dùng.", theme.SUCCESS)
        self._refresh_status()

    def _int8_failed(self, message: str) -> None:
        self._busy = False
        self._set_status(f"Không tải được INT8: {message}", theme.ERROR)
        self._refresh_status()

    def _install_gpu(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.gpu_btn.configure(state="disabled", text="Đang cài...")
        self._set_status("Đang cài PyTorch CUDA (~3 GB) — có thể mất vài phút...",
                         theme.TEXT_DIM)

        def worker() -> None:
            try:
                setup_tools.install_gpu_support(self._set_status)
                self.after(0, self._gpu_done)
            except Exception as exc:
                self.after(0, lambda: self._gpu_failed(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _gpu_done(self) -> None:
        self._busy = False
        self._set_status(
            "Đã cài PyTorch CUDA. Hãy khởi động lại app để dùng GPU.", theme.SUCCESS)
        self._refresh_status()

    def _gpu_failed(self, message: str) -> None:
        self._busy = False
        self._set_status(f"Cài GPU thất bại: {message}", theme.ERROR)
        self._refresh_status()

    def _set_status(self, message: str, color: str = theme.TEXT_DIM) -> None:
        try:
            self.status_label.configure(text=message, text_color=color)
        except Exception:
            pass

    # ── Lưu / Huỷ ──

    def _save(self) -> None:
        self._on_save(self._collect())
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()
