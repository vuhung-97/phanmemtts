from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

import numpy as np

from audio import exporter
from audio.buffer import GrowableBuffer
from audio.speed import apply_speed
from audio.player import AudioPlayer
from core import dialogue
from core.document_reader import read_document
from core.licensing import guard
from engine.dialogue_engine import (DialogueCancelled, render_dialogue)
from engine.tts_engine import TtsEngine
from ui import theme
from ui.components.sync_textbox import SyncTextbox
from ui.shell.page import Page
from ui.ui_kit import Button, Card, SectionTitle

GAP_CHOICES = (("0.25s", 0.25), ("0.5s", 0.5), ("0.75s", 0.75),
               ("1.0s", 1.0), ("1.5s", 1.5))


class DialoguePage(Page):
    """Trang Hội thoại nhiều giọng: kịch bản ``Tên: nội dung`` + bảng giọng."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="dialogue", title="Hội thoại",
                         subtitle="Mỗi dòng: Tên nhân vật: nội dung · dòng # là chú thích",
                         **kwargs)

        self._messages: queue.Queue = queue.Queue()
        self._script = dialogue.DialogueScript()
        self._cast: dict[str, str] = dialogue.load_cast()
        self._voice_rows: dict[str, ctk.CTkComboBox] = {}
        self._pending_parse = None
        self._pending_draft = None
        self._busy = False
        self._active = False
        self._cancel = threading.Event()
        self._player = AudioPlayer()
        self._store = None
        self._timeline = None
        self._base_store = None
        self._base_timeline = None
        self._applied_speed = 1.0
        self._speed_applying = False
        self._pending_speed: float | None = None
        self._playing_preview = False

        self.open_btn = Button(self.header.actions, text="📁  Mở file",
                               variant="secondary", command=self._open_file)
        self.open_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        self.sample_btn = Button(self.header.actions, text="📄  Dán mẫu",
                                 variant="secondary", command=self._insert_sample)
        self.sample_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        self.export_btn = Button(self.header.actions, text="💾  Xuất file",
                                 variant="secondary", command=self._export)
        self.export_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        self.create_btn = Button(self.header.actions, text="⚡  Tạo hội thoại",
                                 variant="primary", command=self._create)
        self.create_btn.pack(side="left")

        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_columnconfigure(1, weight=0, minsize=300)
        self.body.grid_rowconfigure(0, weight=1)

        # ── Trái: kịch bản ──
        left = Card(self.body, padding=theme.SPACE_MD)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, theme.SPACE_MD))
        lbox = left.content
        lbox.grid_columnconfigure(0, weight=1)
        lbox.grid_rowconfigure(1, weight=1)

        SectionTitle(lbox, "Kịch bản",
                     "Dòng thiếu “Tên:” sẽ báo lỗi bên dưới").grid(
            row=0, column=0, sticky="w")
        self.editor = SyncTextbox(lbox, on_text_changed=self._on_text_changed)
        self.editor.grid(row=1, column=0, pady=(theme.SPACE_SM, theme.SPACE_SM),
                         sticky="nsew")

        self.error_box = ctk.CTkFrame(lbox, fg_color="transparent")
        self.error_box.grid(row=2, column=0, sticky="ew")
        self.error_box.grid_columnconfigure(0, weight=1)

        # ── Phải: nhân vật & tuỳ chọn ──
        right = ctk.CTkFrame(self.body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        cast_card = Card(right, padding=theme.SPACE_MD)
        cast_card.grid(row=0, column=0, sticky="nsew")
        cbox = cast_card.content
        cbox.grid_columnconfigure(0, weight=1)
        cbox.grid_rowconfigure(2, weight=1)

        SectionTitle(cbox, "Nhân vật & giọng").grid(row=0, column=0, sticky="w")
        Button(cbox, text="Gán tự động", variant="ghost", size="sm",
               command=self._auto_assign).grid(row=1, column=0,
                                               pady=(theme.SPACE_XS, theme.SPACE_SM),
                                               sticky="w")
        self.cast_scroll = ctk.CTkScrollableFrame(cbox, fg_color=theme.SURFACE)
        self.cast_scroll.grid(row=2, column=0, sticky="nsew")
        self.cast_scroll.grid_columnconfigure(0, weight=1)

        opts = Card(right, padding=theme.SPACE_MD)
        opts.grid(row=1, column=0, sticky="ew", pady=(theme.SPACE_MD, 0))
        obox = opts.content
        obox.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(obox, text="Nghỉ giữa lượt", anchor="w",
                     text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2)).grid(
            row=0, column=0, sticky="w")
        self.gap_combo = ctk.CTkComboBox(
            obox, values=[label for label, _ in GAP_CHOICES], width=86,
            height=30, state="readonly",
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.BORDER, border_width=1,
            button_color=theme.SURFACE_2, button_hover_color=theme.HOVER_BG,
            dropdown_fg_color=theme.SURFACE, dropdown_text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            command=lambda _v: self._save_cast(),
        )
        self.gap_combo.set("0.5s")
        self.gap_combo.grid(row=0, column=1, padx=(theme.SPACE_SM, 0), sticky="e")
        self.summary_label = ctk.CTkLabel(
            obox, text="", anchor="w", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.summary_label.grid(row=1, column=0, columnspan=2,
                                pady=(theme.SPACE_XS, 0), sticky="w")
        self.status_label = ctk.CTkLabel(
            obox, text="", anchor="w", justify="left", wraplength=270,
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.status_label.grid(row=2, column=0, columnspan=2,
                               pady=(theme.SPACE_XS, 0), sticky="w")

        draft = dialogue.load_draft()
        if draft:
            self.editor.set_text(draft)
        self._parse()

    # ── vòng đời ──

    def on_show(self) -> None:
        self._active = True
        bar = self.ctx.shell.player_bar
        bar.set_handlers(
            toggle=self._toggle_play,
            seek=self._seek,
            prev=lambda: self._seek(0.0),
            next=lambda: self._seek(0.0),
            speed=self._on_speed_change,
        )
        bar.set_speed_enabled(True)
        bar.set_speed(self._applied_speed)
        if self._store is not None and self._timeline is not None:
            bar.set_source(self._store, self._sample_rate,
                           self._timeline.sentences)
            bar.set_duration(self._timeline.total_duration)
            bar.set_position(self._player.get_position())
            bar.set_playing(self._player.is_playing)
            bar.set_transport_enabled(True)
        else:
            bar.clear()
        self._refresh_voice_choices()
        self.after(80, self._poll_messages)
        self.after(40, self._tick)

    def on_hide(self) -> None:
        self._active = False
        self._stop_playback()

    # ── soạn thảo ──

    def _on_text_changed(self) -> None:
        if self._pending_parse is not None:
            self.after_cancel(self._pending_parse)
        self._pending_parse = self.after(300, self._parse)
        if self._pending_draft is not None:
            self.after_cancel(self._pending_draft)
        self._pending_draft = self.after(600, self._save_draft)

    def _save_draft(self) -> None:
        self._pending_draft = None
        dialogue.save_draft(self.editor.get_text())

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Mở kịch bản hội thoại",
            filetypes=[
                ("Văn bản", "*.docx;*.txt"),
                ("Word Document", "*.docx"),
                ("Text Document", "*.txt"),
                ("Tất cả", "*.*"),
            ],
            parent=self,
        )
        if not path:
            return
        try:
            self.load_script_file(path)
        except Exception as exc:
            self._set_status(f"Không mở được tệp: {exc}", theme.ERROR)

    def load_script_file(self, path: str) -> None:
        """Nạp kịch bản từ .docx/.txt (tách riêng để test/probe gọi trực tiếp)."""
        content = read_document(path)
        self.editor.set_text(content)
        self._parse()
        self._save_draft()
        self._set_status(f"Đã mở: {Path(path).name}", theme.SUCCESS)

    def _insert_sample(self) -> None:
        self.editor.set_text(dialogue.SAMPLE_SCRIPT)
        self.editor.focus_set()
        self._on_text_changed()
        self._parse()

    def _parse(self) -> None:
        self._pending_parse = None
        self._script = dialogue.parse_script(self.editor.get_text())
        self._render_errors()
        self._render_cast()
        speakers = len(self._script.speakers)
        turns = len(self._script.turns)
        chars = sum(len(t.text) for t in self._script.turns)
        self.summary_label.configure(
            text=f"{speakers} nhân vật · {turns} lượt · {chars} ký tự")
        self.create_btn.configure(
            state="normal" if self._script.ok and not self._busy else "disabled")
        self._save_cast()

    def _render_errors(self) -> None:
        for child in self.error_box.winfo_children():
            child.destroy()
        if self._script.issues:
            preview = "\n".join(str(i) for i in self._script.issues[:4])
            if len(self._script.issues) > 4:
                preview += f"\n… (+{len(self._script.issues) - 4} lỗi)"
            ctk.CTkLabel(
                self.error_box, text=preview, anchor="w", justify="left",
                text_color=theme.ERROR, wraplength=560,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            ).pack(anchor="w")
            for issue in self._script.issues[:4]:
                if issue.line_no:
                    Button(
                        self.error_box, text=f"Sửa dòng {issue.line_no}",
                        variant="ghost", size="sm",
                        command=lambda ln=issue.line_no: self._jump_line(ln),
                    ).pack(anchor="w", pady=(2, 0))
        elif self._script.warnings:
            ctk.CTkLabel(
                self.error_box, text="\n".join(self._script.warnings[:3]),
                anchor="w", justify="left", text_color=theme.WARNING,
                wraplength=560,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            ).pack(anchor="w")

    def _jump_line(self, line_no: int) -> None:
        self.editor._textbox.mark_set("insert", f"{line_no}.0")
        self.editor._textbox.see(f"{line_no}.0")
        self.editor.focus_set()

    # ── bảng giọng ──

    def _enabled_models(self) -> list:
        enabled = getattr(self.ctx, "_all_models", []) or []
        from ui.config import load_enabled_voices

        names = load_enabled_voices()
        if names is None:
            return list(enabled)
        visible = [m for m in enabled if m.model_id in names]
        return visible or list(enabled)

    def _refresh_voice_choices(self) -> None:
        self._parse()

    def _render_cast(self) -> None:
        for child in self.cast_scroll.winfo_children():
            child.destroy()
        self._voice_rows = {}
        models = self._enabled_models()
        display = [m.display_name for m in models]
        if self._script.speakers and any(not self._cast.get(s) for s in
                                         self._script.speakers):
            self._auto_assign(save=False)

        for index, speaker in enumerate(self._script.speakers):
            row = ctk.CTkFrame(self.cast_scroll, fg_color="transparent")
            row.grid(row=index, column=0, padx=2, pady=2, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                row, text=speaker, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1, "bold"),
                text_color=theme.TEXT,
            ).grid(row=0, column=0, sticky="w")

            mid = self._cast.get(speaker, "")
            current = next((m.display_name for m in models
                            if m.model_id == mid), "")
            combo = ctk.CTkComboBox(
                row, values=display or ["(chưa có model)"], height=30,
                state="readonly", width=190,
                fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
                border_color=theme.BORDER, border_width=1,
                button_color=theme.SURFACE_2, button_hover_color=theme.HOVER_BG,
                dropdown_fg_color=theme.SURFACE, dropdown_text_color=theme.TEXT,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
                dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
                command=lambda value, sp=speaker: self._voice_changed(sp, value),
            )
            if current:
                combo.set(current)
            combo.grid(row=1, column=0, pady=(2, 0), sticky="w")
            self._voice_rows[speaker] = combo

            ctk.CTkLabel(
                row, text=f"{self._script.turns_of(speaker)} lượt", anchor="e",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            ).grid(row=0, column=1, padx=(theme.SPACE_XS, 0), sticky="e")
            Button(row, text="🔊", variant="ghost", size="sm", width=32,
                   command=lambda sp=speaker: self._test_speaker(sp)).grid(
                row=1, column=1, padx=(theme.SPACE_XS, 0), sticky="e")

    def _voice_changed(self, speaker: str, display: str) -> None:
        for model in self._enabled_models():
            if model.display_name == display:
                self._cast[speaker] = model.model_id
                break
        self._save_cast()

    def _auto_assign(self, save: bool = True) -> None:
        models = self._enabled_models()
        if not models:
            self._set_status("Chưa có giọng để gán.", theme.ERROR)
            return
        males = [m for m in models if "(Nam" in m.display_name]
        females = [m for m in models if "(Nữ" in m.display_name]
        pool = list(males) + list(females)
        if not pool:
            pool = list(models)
        used: set[str] = set()
        for index, speaker in enumerate(self._script.speakers):
            current = self._cast.get(speaker)
            if current and any(m.model_id == current for m in pool):
                used.add(current)
                continue
            prefer = males if index % 2 == 0 else females
            other = females if prefer is males else males
            candidate = next((m for m in prefer if m.model_id not in used), None)
            if candidate is None:
                candidate = next((m for m in other if m.model_id not in used), None)
            if candidate is None:
                candidate = pool[index % len(pool)]
            self._cast[speaker] = candidate.model_id
            used.add(candidate.model_id)
        if save:
            self._save_cast()
            self._render_cast()
            self._set_status("Đã gán giọng tự động.", theme.SUCCESS)

    def _save_cast(self) -> None:
        cast = {s: self._cast.get(s, "") for s in self._script.speakers}
        dialogue.save_cast({k: v for k, v in cast.items() if v})

    def _test_speaker(self, speaker: str) -> None:
        if self._busy:
            return
        model_id = self._cast.get(speaker)
        if not model_id:
            self._set_status(f"Chưa gán giọng cho '{speaker}'.", theme.ERROR)
            return
        info = next((m for m in (self.ctx._all_models or [])
                     if m.model_id == model_id), None)
        if info is None:
            self._set_status("Không tìm thấy giọng đã chọn.", theme.ERROR)
            return
        self._set_status(f"Đang tạo giọng thử cho {speaker}…", theme.TEXT_DIM)
        threading.Thread(target=self._test_speaker_worker,
                         args=(info, speaker), daemon=True).start()

    def _test_speaker_worker(self, info, speaker: str) -> None:
        try:
            tts = self.ctx._model_manager.load_tts(info)
            tts.set_voice(info.model_id)
            engine = TtsEngine(tts)
            audio, _ = engine.synthesize(
                f"Xin chào, tôi là {speaker}.", speed=1.0)
            self._messages.put(("test_audio", audio, engine.sample_rate, speaker))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── tạo hội thoại ──

    def _create(self) -> None:
        if self._busy:
            self._cancel.set()
            self._set_status("Đang dừng sau lượt hiện tại…", theme.TEXT_DIM)
            return
        if not self._script.ok:
            self._set_status("Sửa các dòng lỗi trước khi tạo hội thoại.",
                             theme.ERROR)
            return
        missing = [s for s in self._script.speakers if not self._cast.get(s)]
        if missing:
            self._set_status(f"Chưa gán giọng cho: {', '.join(missing)}",
                             theme.ERROR)
            return
        infos = []
        for speaker in self._script.speakers:
            info = next((m for m in (self.ctx._all_models or [])
                         if m.model_id == self._cast[speaker]), None)
            if info is None:
                self._set_status(f"Giọng của '{speaker}' không còn trong máy.",
                                 theme.ERROR)
                return
            infos.append(info)
        model = next(m for m in (self.ctx._all_models or [])
                     if m.model_id == self._cast[self._script.speakers[0]])

        self._busy = True
        self._cancel.clear()
        self.create_btn.configure(text="⏹  Dừng", fg_color=theme.DANGER,
                                 hover_color=theme.DANGER_HOVER,
                                 command=self._create)
        self.sample_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.ctx.shell.set_busy(True)
        self._set_status("Đang nạp giọng đọc…", theme.TEXT_DIM)
        threading.Thread(
            target=self._create_worker,
            args=(self._script, dict(self._cast), model, self._gap_sec()),
            daemon=True,
        ).start()

    def _create_worker(self, script, cast: dict, model, gap_sec: float) -> None:
        try:
            tts = self.ctx._model_manager.load_tts(model)
            buffer = GrowableBuffer()

            def progress(turn_i, turn_total, sent_i, sent_total):
                self._messages.put((
                    "status",
                    f"Đang tạo lượt {turn_i}/{turn_total} (câu {sent_i}/{sent_total})…",
                    theme.TEXT_DIM,
                ))

            result = render_dialogue(
                script, tts, cast, gap_sec=gap_sec, speed=1.0, store=buffer,
                progress=progress, cancel=self._cancel,
            )
            self._messages.put(("rendered", result.source, result.sample_rate,
                                result.timeline, script))
        except DialogueCancelled:
            self._messages.put(("cancelled",))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    def _gap_sec(self) -> float:
        label = self.gap_combo.get()
        for name, value in GAP_CHOICES:
            if name == label:
                return value
        return 0.5

    # ── tốc độ ──

    def _on_speed_change(self, value: float) -> None:
        speed = max(float(value), 0.5)
        if self._base_store is None:
            self._set_status("Bấm “Tạo hội thoại” trước khi đổi tốc độ.",
                             theme.TEXT_DIM)
            self.ctx.shell.player_bar.set_speed(self._applied_speed)
            return
        self._pending_speed = speed
        self._request_speed(speed)

    def _request_speed(self, speed: float) -> None:
        if self._speed_applying:
            return
        if abs(speed - self._applied_speed) < 1e-9:
            self._pending_speed = None
            self.ctx.shell.player_bar.set_speed(self._applied_speed)
            return
        self._speed_applying = True
        self._set_status(f"Đang đổi tốc độ {speed:g}x…", theme.TEXT_DIM)
        threading.Thread(
            target=self._speed_worker,
            args=(speed, self._player.get_position(),
                  self._player.is_playing),
            daemon=True,
        ).start()

    def _speed_worker(self, speed: float, position: float,
                      was_playing: bool) -> None:
        try:
            sr = self._sample_rate
            block = max(1, int(sr * 10))
            total = int(self._base_store.total_samples)
            buffer = GrowableBuffer()
            pos = 0
            while pos < total:
                chunk = self._base_store.read(pos, block)
                if chunk is None or chunk.size == 0:
                    break
                buffer.append(apply_speed(
                    np.array(chunk, dtype=np.float32), speed))
                pos += chunk.size
            timeline = self._base_timeline.scaled(speed)
            self._messages.put(("speed_applied", buffer, timeline, speed,
                                position, was_playing))
        except Exception as exc:
            self._messages.put(("speed_error", str(exc)))

    # ── phát / xuất ──

    def _toggle_play(self) -> None:
        if self._store is None:
            self._set_status("Bấm “Tạo hội thoại” trước.", theme.ERROR)
            return
        self._player.toggle()
        self.ctx.shell.player_bar.set_playing(self._player.is_playing)

    def _seek(self, seconds: float) -> None:
        if self._store is None:
            return
        self._player.seek(float(seconds))
        self.ctx.shell.player_bar.set_position(self._player.get_position())

    def _stop_playback(self) -> None:
        try:
            if self._player.is_playing or self._player.is_buffering:
                self._player.pause()
        except Exception:
            pass
        self.ctx.shell.player_bar.set_playing(False)

    def _export(self) -> None:
        if self._store is None:
            self._set_status("Chưa có audio — bấm “Tạo hội thoại” trước.",
                             theme.ERROR)
            return
        if not self.ctx._ensure_license("xuất file"):
            return
        path = filedialog.asksaveasfilename(
            title="Xuất hội thoại", defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav")], parent=self)
        if not path:
            return
        try:
            out = exporter.export_source(self._store, self._sample_rate, path)
        except Exception as exc:
            self._set_status(f"Lỗi xuất file: {exc}", theme.ERROR)
            return
        try:
            self.ctx._history.add(
                out, voice="Hội thoại", speed=1.0,
                duration=float(self._timeline.sentences[-1].end_sec)
                if self._timeline and self._timeline.sentences else 0.0,
                chars=len(self.editor.get_text()),
                preview=", ".join(self._script.speakers),
            )
        except Exception:
            pass
        try:
            history = self.ctx._export_history
            history.append(str(out))
            del history[:-10]
        except Exception:
            pass
        self._set_status(f"Đã xuất: {out}", theme.SUCCESS)
        self.ctx.shell.status(f"Đã xuất hội thoại: {out}", theme.SUCCESS)

    def _tick(self) -> None:
        if not self._active:
            return
        ended = self._player.update()
        bar = self.ctx.shell.player_bar
        if self._player.is_playing:
            bar.set_position(self._player.get_position())
            bar.set_playing(True)
        if ended:
            bar.set_playing(False)
            bar.set_position(0.0)
        self.after(40, self._tick)

    # ── message loop ──

    def _set_status(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _poll_messages(self) -> None:
        try:
            while True:
                msg = self._messages.get_nowait()
                kind = msg[0]
                if kind == "status":
                    _, text, color = msg
                    self._set_status(text, color)
                elif kind == "test_audio":
                    _, audio, sr, speaker = msg
                    self._player.stop()
                    self._player.load(audio, sr, has_more=False)
                    self._player.play()
                    bar = self.ctx.shell.player_bar
                    source = GrowableBuffer()
                    source.append(audio)
                    bar.set_source(source, sr)
                    bar.set_duration(len(audio) / sr if sr else 0.0)
                    bar.set_playing(True)
                    self._set_status(f"Đang nghe thử giọng {speaker}.",
                                     theme.SUCCESS)
                elif kind == "rendered":
                    _, store, sr, timeline, script = msg
                    self._base_store = store
                    self._base_timeline = timeline
                    self._store = store
                    self._timeline = timeline
                    self._sample_rate = sr
                    self._applied_speed = 1.0
                    self._busy = False
                    self.ctx.shell.set_busy(False)
                    self._reset_create_button()
                    bar = self.ctx.shell.player_bar
                    bar.set_source(store, sr, timeline.sentences)
                    bar.set_duration(timeline.total_duration)
                    bar.set_position(0.0)
                    self._player.stop()
                    self._player.load_source(store, sr, has_more=False)
                    self._player.play()
                    bar.set_playing(True)
                    self._set_status(
                        f"Xong: {len(timeline.sentences)} câu, "
                        f"{timeline.total_duration:.1f} giây.", theme.SUCCESS)
                    speed = bar.get_speed()
                    if abs(speed - 1.0) > 1e-9:
                        self._request_speed(speed)
                elif kind == "speed_applied":
                    _, store, timeline, speed, position, was_playing = msg
                    self._speed_applying = False
                    old_speed = self._applied_speed or 1.0
                    self._store = store
                    self._timeline = timeline
                    self._applied_speed = speed
                    self._sample_rate = timeline.sample_rate
                    duration = timeline.total_duration
                    new_pos = (min(position * old_speed / speed, duration)
                               if speed > 0 else 0.0)
                    self._player.stop()
                    self._player.load_source(store, timeline.sample_rate,
                                             has_more=False)
                    if new_pos > 0:
                        self._player.seek(new_pos)
                    if was_playing:
                        self._player.play()
                    bar = self.ctx.shell.player_bar
                    bar.set_speed(speed)
                    bar.set_source(store, timeline.sample_rate,
                                   timeline.sentences)
                    bar.set_duration(duration)
                    bar.set_position(new_pos)
                    bar.set_playing(was_playing)
                    self._set_status(f"Đã áp tốc độ {speed:g}x.",
                                     theme.SUCCESS)
                    pending = self._pending_speed
                    self._pending_speed = None
                    if pending is not None and abs(pending - speed) > 1e-9:
                        self._request_speed(pending)
                elif kind == "speed_error":
                    _, text = msg
                    self._speed_applying = False
                    self._pending_speed = None
                    self.ctx.shell.player_bar.set_speed(self._applied_speed)
                    self._set_status(f"Lỗi đổi tốc độ: {text}", theme.ERROR)
                elif kind == "cancelled":
                    self._busy = False
                    self.ctx.shell.set_busy(False)
                    self._reset_create_button()
                    self._set_status("Đã dừng tạo hội thoại.", theme.TEXT_DIM)
                elif kind == "error":
                    _, text = msg
                    self._busy = False
                    self.ctx.shell.set_busy(False)
                    self._reset_create_button()
                    self._set_status(f"Lỗi: {text}", theme.ERROR)
        except queue.Empty:
            pass
        if self._active:
            self.after(80, self._poll_messages)

    def _reset_create_button(self) -> None:
        self.create_btn.configure(text="⚡  Tạo hội thoại",
                                  fg_color=theme.PRIMARY,
                                  hover_color=theme.PRIMARY_HOVER,
                                  command=self._create)
        self.sample_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        self.create_btn.configure(
            state="normal" if self._script.ok else "disabled")
