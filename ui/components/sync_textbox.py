from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme

ACTIVE_TAG = "active_sentence"


class SyncTextbox(ctk.CTkTextbox):
    """Hộp văn bản: highlight câu đang đọc (không tua khi click — dùng seekbar)."""

    def __init__(self, master, on_text_changed: Callable[[], None], **kwargs) -> None:
        kwargs.setdefault("font", (theme.FONT_FAMILY, theme.FONT_SIZE + 2))
        kwargs.setdefault("wrap", "word")
        kwargs.setdefault("fg_color", theme.SURFACE)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.SIDEBAR_DIVIDER)
        super().__init__(master, **kwargs)
        self._on_text_changed = on_text_changed

        inner = self._textbox
        inner.tag_configure(ACTIVE_TAG, background=theme.HIGHLIGHT_BG,
                            foreground=theme.HIGHLIGHT_FG)
        inner.bind("<Key>", self._on_key, add="+")

    def set_text(self, text: str) -> None:
        self.delete("1.0", "end")
        self.insert("1.0", text)
        self._textbox.edit_modified(False)

    def get_text(self) -> str:
        return self.get("1.0", "end-1c")

    def highlight_span(self, char_start: int, char_end: int) -> None:
        inner = self._textbox
        inner.tag_remove(ACTIVE_TAG, "1.0", "end")
        start_idx = f"1.0 + {char_start} chars"
        end_idx = f"1.0 + {char_end} chars"
        inner.tag_add(ACTIVE_TAG, start_idx, end_idx)
        inner.see(start_idx)

    def clear_highlight(self) -> None:
        self._textbox.tag_remove(ACTIVE_TAG, "1.0", "end")

    def _on_key(self, event) -> None:
        if event.keysym in ("BackSpace", "Delete", "Return", "Enter") or (
            event.state & 0x4 and event.keysym.lower() in ("v", "x", "a")
        ):
            self.clear_highlight()
            self.after(50, self._on_text_changed)
