from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import version
from core.document_reader import read_document
from core.text_processor import clean_for_reading
from engine.tts_engine import TtsEngine
from ui import theme
from ui.components.history_dialog import HistoryDialog, open_in_system
from ui.components.voice_manager import VoiceManagerDialog
from ui.config import (load_enabled_voices, save_enabled_voices, save_settings)


class ToolsMixin:
    """Model, giọng đọc, cài đặt, lịch sử, trợ giúp và mở file."""

    # ── Scan & voice management ──

    def _scan_models(self) -> list:
        prev = None
        try:
            prev = self.topbar.get_selected_voice()
        except Exception:
            pass
        self._all_models = self._model_manager.scan()
        if not self._all_models:
            self.topbar.set_status(self._bundle_problem(), theme.ERROR)
            return self._all_models

        enabled = load_enabled_voices()
        if enabled is not None:
            visible = [m for m in self._all_models if m.model_id in enabled]
        else:
            visible = self._all_models

        if not visible:
            self.topbar.set_voices([], None)
            self.topbar.set_status(
                "Tất cả giọng đều bị tắt — bấm ＋ Thêm để bật lại.", theme.ERROR)
            return self._all_models

        names = [m.display_name for m in visible]
        selected = prev if prev in names else names[0]
        self.topbar.set_voices(names, selected)
        if hasattr(self, "shell"):
            self.shell.set_voices(len(self._all_models), len(self._all_models))
        self.topbar.set_status(
            f"{len(names)}/{len(self._all_models)} giọng sẵn sàng.", theme.TEXT_DIM)
        return self._all_models

    def _bundle_problem(self) -> str:
        """Thông báo khi không thấy model: nêu rõ file nào thiếu trong bộ cài."""
        try:
            from engine import setup_tools

            missing = setup_tools.verify_bundle()
        except Exception:
            missing = []
        if not missing:
            return "Không tìm thấy mô hình trong thư mục 'models/'."
        preview = ", ".join(missing[:3])
        more = f"… (+{len(missing) - 3})" if len(missing) > 3 else ""
        return (f"Bộ cài thiếu {len(missing)} file model: {preview}{more}. "
                "Hãy chép lại thư mục 'models/' từ bộ cài gốc.")

    def _selected_model(self):
        name = self.topbar.get_selected_voice()
        for m in self._all_models:
            if m.display_name == name:
                return m
        return None

    def _open_voice_manager(self) -> None:
        if hasattr(self, "shell") and self.shell.has_page("voices"):
            self.shell.show("voices")
            return
        enabled = load_enabled_voices()
        if enabled is None:
            enabled = {m.model_id for m in self._all_models}

        def on_save(new_enabled: set[str]) -> None:
            save_enabled_voices(new_enabled)
            self._scan_models()

        def on_voice_changed(name: str) -> None:
            # Ghi đè/xóa giọng đang được nạp -> giải phóng, lần sinh sau tải lại
            self._model_manager.unload_if(f"vieneu:{name}")

        VoiceManagerDialog(
            self, self._all_models, enabled, on_save,
            get_models=self._scan_models,
            on_voice_changed=on_voice_changed,
        )

    # ── Từ điển phát âm & làm sạch văn bản ──

    def _open_dictionary(self) -> None:
        if hasattr(self, "shell") and self.shell.has_page("dictionary"):
            self.shell.show("dictionary")
            return
        from ui.components.dictionary_dialog import DictionaryDialog

        DictionaryDialog(self, on_changed=self._on_dictionary_changed)

    def _on_dictionary_changed(self) -> None:
        """Từ điển đổi -> âm thanh đã tổng hợp không còn đúng."""
        if self._synth_text is not None:
            self._invalidate_audio(
                "Đã đổi từ điển phát âm — bấm Chuyển đổi để áp dụng.")
        else:
            self.topbar.set_status("Đã cập nhật từ điển phát âm.", theme.SUCCESS)

    def _clean_text(self) -> None:
        """Bỏ dòng trống thừa + gộp dòng ngắt giữa câu (hoàn tác được)."""
        text = self.textbox.get_text()
        if not text.strip():
            self.topbar.set_status("Không có nội dung để làm sạch.", theme.ERROR)
            return
        cleaned, changes = clean_for_reading(text)
        if changes == 0 or cleaned == text:
            self.topbar.set_status(
                "Văn bản đã sạch, không cần thay đổi.", theme.TEXT_DIM)
            return
        self.textbox.replace_all(cleaned)
        self._refresh_tag_hint()
        self.topbar.set_status(
            f"Đã làm sạch {changes} chỗ. Bấm Ctrl+Z nếu muốn hoàn tác.",
            theme.SUCCESS)

    # ── Cài đặt ──

    def _open_settings(self) -> None:
        if hasattr(self, "shell") and self.shell.has_page("settings"):
            self.shell.show("settings")
            return
        from ui.components.settings_dialog import SettingsDialog

        def on_save(settings: dict) -> None:
            changed = (
                settings["precision"] != self._settings["precision"]
                or settings["threads"] != self._settings["threads"]
            )
            self._settings = dict(settings)
            save_settings(settings)
            if changed:
                self._model_manager.set_runtime(
                    precision=settings["precision"], threads=settings["threads"])
                self.topbar.set_status(
                    "Đã cập nhật cấu hình model — giọng sẽ nạp lại khi chuyển đổi.",
                    theme.TEXT_DIM)
            else:
                self.topbar.set_status("Đã lưu cài đặt.", theme.SUCCESS)

        SettingsDialog(self, dict(self._settings), on_save)

    # ── Lịch sử bản dựng ──

    def _open_history(self) -> None:
        if hasattr(self, shell) and self.shell.has_page(history):
            self.shell.show(history)
            return
        HistoryDialog(self, self._history)

    # ── Trợ giúp ──

    def _open_terms(self) -> None:
        """Xem lại điều khoản (chỉ đọc)."""
        from ui.components.terms_dialog import TermsDialog

        TermsDialog(self, require_accept=False)

    def _open_help(self) -> None:
        """Mở file hướng dẫn đi kèm (bản cài: HUONG_DAN_V3.txt, dev: docs/*.docx)."""
        from core.paths import app_dir

        candidates = [app_dir() / "HUONG_DAN_V3.txt"]
        candidates += sorted(app_dir().glob("docs/Huong_dan_su_dung_*.docx"), reverse=True)
        for path in candidates:
            if path.exists():
                open_in_system(path)
                self.topbar.set_status(f"Đã mở hướng dẫn: {path.name}", theme.SUCCESS)
                return
        self.topbar.set_status(
            "Không tìm thấy file hướng dẫn trong thư mục cài đặt.", theme.ERROR)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Giới thiệu",
            f"{version.__app_name__}\n"
            f"Phiên bản {version.__version__}\n\n"
            "Chuyển văn bản thành giọng nói tiếng Việt, chạy hoàn toàn offline trên CPU.\n"
            "Không gửi dữ liệu ra ngoài.",
            parent=self,
        )

    # Chức năng ghép nhạc (đấu dây từ TopBar qua on_merge).
    def _open_merge_dialog(self) -> None:
        if hasattr(self, "shell") and self.shell.has_page("merge"):
            self.shell.show("merge")
            return
        if not self._ensure_license("ghép nhạc"):
            return
        from ui.components.merge_dialog import MergeDialog

        MergeDialog(
            self,
            export_history=self._export_history,
            on_merged=lambda path: self.topbar.set_status(
                f"Đã ghép: {path}", theme.SUCCESS),
        )

    # ── Chuyển đổi hàng loạt ──

    def _open_batch_dialog(self) -> None:
        if hasattr(self, shell) and self.shell.has_page(batch):
            self.shell.show(batch)
            return
        if self._busy:
            self.topbar.set_status(
                "Đang chuyển đổi — dừng lại trước khi xuất hàng loạt.",
                theme.ERROR)
            return
        if not self._ensure_license("xuất nhiều tệp"):
            return
        model = self._selected_model()
        if model is None:
            self.topbar.set_status("Không có giọng đọc để xuất.", theme.ERROR)
            return
        from ui.components.batch_dialog import BatchDialog

        BatchDialog(
            self,
            text=self.textbox.get_text(),
            model=model,
            model_manager=self._model_manager,
            voice_name=self.topbar.get_selected_voice() or "",
            speed=self.topbar.get_speed(),
            on_done=lambda message: self.topbar.set_status(message, theme.SUCCESS),
        )

    # ── Test giọng ──

    def _test_voice(self) -> None:
        model = self._selected_model()
        if model is None:
            self.topbar.set_status("Không có giọng để test.", theme.ERROR)
            return
        test_text = self.topbar.get_test_text()
        speed = self.topbar.get_speed()
        self.topbar.set_status(f"Đang nạp {model.display_name}...", theme.TEXT_DIM)
        threading.Thread(target=self._test_voice_worker,
                         args=(model, test_text, speed), daemon=True).start()

    def _test_voice_worker(self, model, test_text: str, speed: float) -> None:
        try:
            tts = self._model_manager.load_tts(model)
            engine = TtsEngine(tts)
            self._messages.put(("status", "Đang tạo âm thanh test...", theme.TEXT_DIM))
            audio, _ = engine.synthesize(test_text, speed=speed)
            self._messages.put(("status", "Đang phát test...", theme.SUCCESS))
            self._player.load(audio, engine.sample_rate, has_more=False)
            self._player.play()
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── Mở file ──

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file văn bản",
            filetypes=[
                ("Văn bản", "*.docx;*.txt"),
                ("Word Document", "*.docx"),
                ("Text Document", "*.txt"),
                ("Tất cả tập tin", "*.*"),
            ],
        )
        if not path:
            return
        try:
            content = read_document(path)
            self.textbox.set_text(content)
            self.topbar.set_source_name(Path(path).name)
            self.topbar.set_status(f"Đã mở: {path}", theme.SUCCESS)
            self._refresh_tag_hint()
        except Exception as exc:
            self.topbar.set_status(f"Không mở được file: {exc}", theme.ERROR)
