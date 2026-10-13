from __future__ import annotations

import queue
import threading
from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.config import load_test_text


class VoiceManagerDialog(ctk.CTkToplevel):
    """Dialog modal: checklist giọng đọc + test + lưu/huỷ."""

    def __init__(self, master, all_models: list, enabled_ids: set[str],
                 on_save: Callable[[set[str]], None]) -> None:
        super().__init__(master)
        self.title("Quản lý giọng đọc")
        self.geometry("500x620")
        self.minsize(420, 480)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._all_models = all_models
        self._on_save = on_save
        self._checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self._test_player = None
        self._test_busy = False
        self._messages: queue.Queue = queue.Queue()

        self._build_ui(enabled_ids)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _: self._cancel())
        self.after(50, self._poll_messages)

    # ── UI ──

    def _build_ui(self, enabled_ids: set[str]) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Tiêu đề
        ctk.CTkLabel(
            self, text="Chọn giọng hiển thị trong combobox",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 2, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        # Danh sách checkbox (scroll)
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=theme.SURFACE, corner_radius=8,
        )
        scroll.grid(row=1, column=0, padx=20, pady=8, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        for i, model in enumerate(self._all_models):
            var = ctk.BooleanVar(value=model.model_id in enabled_ids)
            cb = ctk.CTkCheckBox(
                scroll, text=model.display_name, variable=var,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                text_color=theme.TEXT, hover_color=theme.ACCENT,
                fg_color=theme.ACCENT, corner_radius=4,
            )
            cb.grid(row=i, column=0, padx=12, pady=3, sticky="w")
            self._checkboxes[model.model_id] = cb

        # Hàng nút: Tất cả / Bỏ chọn / Test
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=2, column=0, padx=20, pady=(0, 4), sticky="ew")
        mid.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            mid, text="☑ Tất cả", height=30,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._select_all,
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            mid, text="□ Bỏ chọn", height=30,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._deselect_all,
        ).grid(row=0, column=1, padx=4, sticky="ew")

        self.test_btn = ctk.CTkButton(
            mid, text="🔊 Test giọng", height=30,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._test_selected,
        )
        self.test_btn.grid(row=0, column=2, padx=(4, 0), sticky="ew")

        # Status test
        self.test_status = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), wraplength=460,
        )
        self.test_status.grid(row=3, column=0, padx=20, pady=(0, 4), sticky="w")

        # Hàng nút cuối: Lưu / Huỷ
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, padx=20, pady=(4, 16), sticky="ew")
        bottom.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            bottom, text="💾 Lưu", height=36, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._save,
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            bottom, text="✕ Huỷ", height=36,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._cancel,
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    # ── actions ──

    def _select_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.select()

    def _deselect_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.deselect()

    def _collect_checked(self) -> set[str]:
        return {
            mid for mid, cb in self._checkboxes.items()
            if cb.get()
        }

    def _save(self) -> None:
        checked = self._collect_checked()
        self._stop_test()
        self._on_save(checked)
        self.destroy()

    def _cancel(self) -> None:
        self._stop_test()
        self.destroy()

    # ── test giọng ──

    def _test_selected(self) -> None:
        if self._test_busy:
            return
        checked = self._collect_checked()
        if not checked:
            self.test_status.configure(text="Chưa chọn giọng nào để test.",
                                       text_color=theme.ERROR)
            return
        first_id = sorted(checked)[0]
        model = next((m for m in self._all_models if m.model_id == first_id), None)
        if model is None:
            return
        self._test_busy = True
        self.test_btn.configure(state="disabled")
        self.test_status.configure(text=f"Đang nạp {model.display_name}...",
                                   text_color=theme.TEXT_DIM)
        threading.Thread(
            target=self._test_worker, args=(model,), daemon=True,
        ).start()

    def _test_worker(self, model) -> None:
        try:
            from engine.model_manager import ModelManager
            from engine.tts_engine import TtsEngine
            from audio.player import AudioPlayer

            self._messages.put(("status", "Đang tạo âm thanh test...", theme.TEXT_DIM))
            mm = ModelManager()
            tts = mm.load_tts(model)
            engine = TtsEngine(tts)
            audio, _ = engine.synthesize(load_test_text())

            player = AudioPlayer()
            player.load(audio, engine.sample_rate, has_more=False)
            player.play()
            self._test_player = player
            self._messages.put(("status", "Đang phát test...", theme.SUCCESS))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    def _stop_test(self) -> None:
        if self._test_player is not None:
            try:
                self._test_player.stop()
                self._test_player.quit()
            except Exception:
                pass
            self._test_player = None

    def _poll_messages(self) -> None:
        try:
            while True:
                msg = self._messages.get_nowait()
                kind = msg[0]
                if kind == "status":
                    _, text, color = msg
                    self.test_status.configure(text=text, text_color=color)
                elif kind == "error":
                    _, text = msg
                    self.test_status.configure(
                        text=f"Lỗi: {text}", text_color=theme.ERROR)
                    self._test_busy = False
                    self.test_btn.configure(state="normal")
        except queue.Empty:
            pass
        # Khi player hết phát → reset nút test
        if self._test_player is not None and not self._test_player.is_playing:
            self._test_busy = False
            self.test_btn.configure(state="normal")
            self._test_player = None
        self.after(80, self._poll_messages)
