"""Hộp thoại quản lý từ điển phát âm.

Ví dụ: ``KTX`` -> ``ký túc xá``, ``TP.HCM`` -> ``thành phố Hồ Chí Minh``.

Lưu ngay mỗi thao tác (thêm/sửa/xoá/bật-tắt) xuống
``data_dir()/pronunciation-dict.json`` — không cần nút "Lưu".
"""

from __future__ import annotations

from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from core import dictionary
from ui import theme

_MAX_ROWS_SHOWN = 200


class DictionaryDialog(ctk.CTkToplevel):
    """Bảng từ điển + form thêm/sửa + nhập/xuất tệp."""

    def __init__(self, master, on_changed: Callable[[], None] | None = None) -> None:
        super().__init__(master)
        self.title("Từ điển phát âm")
        self.geometry("760x640")
        self.minsize(620, 520)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._on_changed = on_changed
        self._doc = dictionary.load()
        self._filter = ""
        self._editing: dict | None = None   # mục đang sửa

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _: self._close())

    # ── UI ──

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, padx=18, pady=(14, 4), sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            head, text="Từ điển phát âm",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 3, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w")

        self.enable_var = ctk.BooleanVar(value=bool(self._doc.get("enabled", True)))
        self.enable_switch = ctk.CTkSwitch(
            head, text="Bật từ điển", variable=self.enable_var,
            command=self._toggle_enabled,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            text_color=theme.TEXT, progress_color=theme.ACCENT,
        )
        self.enable_switch.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            head,
            text="Thay cách viết trước khi đọc (không áp dụng trong thẻ [..]).",
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        ).grid(row=1, column=0, columnspan=2, pady=(2, 0), sticky="w")

        # ── Form thêm / sửa ──
        form = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=8,
                            border_width=1, border_color=theme.SIDEBAR_DIVIDER)
        form.grid(row=1, column=0, padx=18, pady=8, sticky="ew")
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)

        self.src_entry = self._entry(form, "Cụm cần thay", row=0, column=0)
        self.dst_entry = self._entry(form, "Cách đọc", row=0, column=2)

        opts = ctk.CTkFrame(form, fg_color="transparent")
        opts.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 6), sticky="w")
        self.whole_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts, text="Nguyên từ (không khớp bên trong từ khác)",
            variable=self.whole_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, fg_color=theme.ACCENT, hover_color=theme.ACCENT,
            corner_radius=4,
        ).pack(side="left", padx=(0, 10))
        self.case_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opts, text="Phân biệt hoa/thường", variable=self.case_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, fg_color=theme.ACCENT, hover_color=theme.ACCENT,
            corner_radius=4,
        ).pack(side="left")

        self.add_btn = ctk.CTkButton(
            form, text="＋ Thêm", height=32, width=110,
            fg_color=theme.DARK_BUTTON_BG, hover_color=theme.DARK_BUTTON_HOVER,
            text_color=theme.DARK_BUTTON_TEXT, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._save_entry,
        )
        self.add_btn.grid(row=2, column=3, padx=(6, 10), pady=(0, 8), sticky="e")
        self.clear_btn = ctk.CTkButton(
            form, text="✕ Bỏ chọn", height=32, width=100,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT_DIM, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=self._clear_form,
        )
        self.clear_btn.grid(row=2, column=2, padx=(0, 4), pady=(0, 8), sticky="e")
        self.edit_hint = ctk.CTkLabel(
            form, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.edit_hint.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 8),
                            sticky="w")

        # ── Danh sách ──
        list_frame = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=8,
                                  border_width=1, border_color=theme.SIDEBAR_DIVIDER)
        list_frame.grid(row=2, column=0, padx=18, pady=(4, 8), sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        search_row = ctk.CTkFrame(list_frame, fg_color="transparent")
        search_row.grid(row=0, column=0, padx=8, pady=(8, 4), sticky="ew")
        search_row.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(
            search_row, height=30, placeholder_text="Tìm trong từ điển…",
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)
        self.count_label = ctk.CTkLabel(
            search_row, text="", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.count_label.grid(row=0, column=1, padx=(8, 4))

        self._list = ctk.CTkScrollableFrame(list_frame, fg_color=theme.SURFACE)
        self._list.grid(row=1, column=0, padx=4, pady=(0, 6), sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        # ── Chân ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=18, pady=(0, 14), sticky="ew")
        bottom.grid_columnconfigure(2, weight=1)
        for col, (text, cmd) in enumerate((
            ("⬆ Nhập tệp…", self._import_file),
            ("⬇ Xuất tệp…", self._export_file),
        )):
            ctk.CTkButton(
                bottom, text=text, height=32, width=110,
                fg_color="transparent", border_width=1,
                border_color=theme.SIDEBAR_DIVIDER, text_color=theme.TEXT,
                hover_color=theme.SURFACE, corner_radius=8,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                command=cmd,
            ).grid(row=0, column=col, padx=(0, 6), sticky="w")

        self.status_label = ctk.CTkLabel(
            bottom, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.status_label.grid(row=0, column=2, padx=(6, 6), sticky="ew")

        ctk.CTkButton(
            bottom, text="Đóng", height=32, width=90,
            fg_color=theme.DARK_BUTTON_BG, hover_color=theme.DARK_BUTTON_HOVER,
            text_color=theme.DARK_BUTTON_TEXT, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._close,
        ).grid(row=0, column=3, sticky="e")

        self._render_list()

    def _entry(self, parent, label: str, row: int, column: int) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent, text=label, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2, "bold"),
        ).grid(row=row, column=column, padx=(10, 4), pady=(10, 0), sticky="w")
        entry = ctk.CTkEntry(
            parent, height=32, fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        entry.grid(row=row, column=column + 1, padx=(0, 10), pady=(10, 0), sticky="ew")
        entry.bind("<Return>", lambda _e: self._save_entry())
        return entry

    # ── Danh sách ──

    def _visible_entries(self) -> list[dict]:
        needle = self._filter.casefold()
        entries = self._doc.get("entries") or []
        if needle:
            entries = [
                e for e in entries
                if needle in e["from"].casefold() or needle in e["to"].casefold()
            ]
        return entries[:_MAX_ROWS_SHOWN]

    def _render_list(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()

        entries = self._visible_entries()
        total = len(self._doc.get("entries") or [])
        self.count_label.configure(
            text=f"{len(entries)}/{total}" if len(entries) != total else f"{total} mục")
        if not entries:
            ctk.CTkLabel(
                self._list,
                text=("Không có mục nào." if total == 0
                      else "Không tìm thấy mục phù hợp."),
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=0, padx=10, pady=16, sticky="w")
            return

        disabled = not self.enable_var.get()
        for i, item in enumerate(entries):
            row = ctk.CTkFrame(self._list, fg_color="transparent")
            row.grid(row=i, column=0, padx=2, pady=1, sticky="ew")
            row.grid_columnconfigure(1, weight=1)

            button = ctk.CTkButton(
                row, text=item["from"], height=28, width=170, anchor="w",
                fg_color="transparent", hover_color=theme.HOVER_BG,
                text_color=theme.TEXT_DIM if disabled else theme.TEXT,
                corner_radius=6,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                command=lambda it=item: self._load_entry(it),
            )
            button.grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                row, text="→", text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=1, padx=(2, 6), sticky="w")

            ctk.CTkLabel(
                row, text=item["to"], text_color=theme.TEXT, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=2, sticky="w")

            flags = []
            if item.get("case_sensitive"):
                flags.append("hoa/thường")
            if not item.get("whole_word", True):
                flags.append("một phần")
            if flags:
                ctk.CTkLabel(
                    row, text=" · ".join(flags), text_color=theme.TEXT_DIM,
                    font=(theme.FONT_FAMILY, theme.FONT_SIZE - 3),
                ).grid(row=0, column=3, padx=(6, 4))

            ctk.CTkButton(
                row, text="🗑", width=30, height=24,
                fg_color="transparent", border_width=1, border_color=theme.ERROR,
                text_color=theme.ERROR, hover_color=theme.SURFACE, corner_radius=4,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                command=lambda it=item: self._delete_entry(it),
            ).grid(row=0, column=4, padx=(4, 2))

    def _on_search(self, _event=None) -> None:
        self._filter = self.search_entry.get().strip()
        self._render_list()

    # ── Thao tác ──

    def _load_entry(self, item: dict) -> None:
        self._editing = item
        self._set_entry(self.src_entry, item["from"])
        self._set_entry(self.dst_entry, item["to"])
        self.whole_var.set(bool(item.get("whole_word", True)))
        self.case_var.set(bool(item.get("case_sensitive", False)))
        self.add_btn.configure(text="💾 Cập nhật")
        self.edit_hint.configure(text=f"Đang sửa: {item['from']}")

    def _clear_form(self) -> None:
        self._editing = None
        self._set_entry(self.src_entry, "")
        self._set_entry(self.dst_entry, "")
        self.whole_var.set(True)
        self.case_var.set(False)
        self.add_btn.configure(text="＋ Thêm")
        self.edit_hint.configure(text="")
        self.src_entry.focus_set()

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)

    def _save_entry(self) -> None:
        try:
            src, dst = dictionary.validate_entry(
                self.src_entry.get(), self.dst_entry.get())
        except ValueError as exc:
            self._set_status(str(exc), theme.ERROR)
            return

        new_entry = {
            "from": src,
            "to": dst,
            "whole_word": bool(self.whole_var.get()),
            "case_sensitive": bool(self.case_var.get()),
        }
        entries = list(self._doc.get("entries") or [])
        if self._editing is not None:
            entries = [e for e in entries if not self._same_entry(e, self._editing)]
        else:
            dup = self._find_duplicate(src, entries)
            if dup is not None:
                entries.remove(dup)
        entries.append(new_entry)
        self._doc["entries"] = entries
        self._persist()
        self._clear_form()
        self._set_status(f"Đã lưu: {src} → {dst}", theme.SUCCESS)

    @staticmethod
    def _same_entry(a: dict, b: dict) -> bool:
        return (a.get("from") == b.get("from")
                and bool(a.get("case_sensitive")) == bool(b.get("case_sensitive")))

    def _find_duplicate(self, source: str, entries: list[dict]) -> dict | None:
        for entry in entries:
            same = (entry["from"] == source
                    if entry.get("case_sensitive") else
                    entry["from"].casefold() == source.casefold())
            if same:
                return entry
        return None

    def _delete_entry(self, item: dict) -> None:
        if not messagebox.askyesno(
                "Xoá mục?", f"Xoá '{item['from']}' khỏi từ điển?", parent=self):
            return
        self._doc["entries"] = [
            e for e in (self._doc.get("entries") or []) if e["from"] != item["from"]
        ]
        if self._editing is not None and self._same_entry(self._editing, item):
            self._clear_form()
        self._persist()
        self._set_status(f"Đã xoá: {item['from']}", theme.TEXT_DIM)

    def _toggle_enabled(self) -> None:
        self._doc["enabled"] = bool(self.enable_var.get())
        self._persist()
        self._render_list()
        state = "bật" if self._doc["enabled"] else "tắt"
        self._set_status(f"Đã {state} từ điển.", theme.SUCCESS)

    def _persist(self) -> None:
        try:
            dictionary.save(self._doc)
        except OSError as exc:
            self._set_status(f"Không ghi được từ điển: {exc}", theme.ERROR)
            return
        if self._on_changed is not None:
            self._on_changed()
        self._render_list()

    # ── Nhập / xuất ──

    def _import_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn tệp từ điển (.json)",
            filetypes=[("Từ điển JSON", "*.json"), ("Tất cả", "*.*")],
            parent=self,
        )
        if not path:
            return
        incoming = dictionary.load(path)
        if not incoming["entries"]:
            self._set_status("Tệp không có mục hợp lệ nào.", theme.ERROR)
            return
        mode = messagebox.askyesnocancel(
            "Nhập từ điển",
            f"Tệp có {len(incoming['entries'])} mục.\n\n"
            "Có = gộp vào danh sách hiện tại\n"
            "Không = thay toàn bộ danh sách\n"
            "Huỷ = không làm gì",
            parent=self,
        )
        if mode is None:
            return
        if mode:
            merged = dict(self._doc)
            entries = {e["from"].casefold(): e for e in merged.get("entries") or []}
            for entry in incoming["entries"]:
                entries[entry["from"].casefold()] = entry
            merged["entries"] = list(entries.values())
            self._doc = merged
        else:
            incoming["enabled"] = self._doc.get("enabled", True)
            self._doc = incoming
        self.enable_var.set(bool(self._doc.get("enabled", True)))
        self._persist()
        self._set_status(f"Đã nhập {len(incoming['entries'])} mục.", theme.SUCCESS)

    def _export_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Xuất từ điển",
            initialfile=dictionary.DICT_FILENAME,
            defaultextension=".json",
            filetypes=[("Từ điển JSON", "*.json"), ("Tất cả", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            dictionary.save(self._doc, path)
        except OSError as exc:
            self._set_status(f"Không xuất được: {exc}", theme.ERROR)
            return
        self._set_status(f"Đã xuất: {path}", theme.SUCCESS)

    def _set_status(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
