from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

from core import dictionary
from ui import theme
from ui.shell.page import Page
from ui.ui_kit import Button, Card, SectionTitle

_MAX_ROWS = 200


class DictionaryPage(Page):
    """Trang Từ điển phát âm: bảng mục + form thêm/sửa + nhập/xuất."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="dictionary", title="Từ điển phát âm",
                         subtitle="Thay cách đọc từ viết tắt / tên riêng trước khi đọc",
                         **kwargs)
        self._doc = dictionary.load()
        self._filter = ""
        self._editing: dict | None = None

        Button(self.header.actions, text="Nhập tệp…", variant="secondary",
               command=self._import_file).pack(side="left", padx=(0, theme.SPACE_SM))
        Button(self.header.actions, text="Xuất tệp…", variant="secondary",
               command=self._export_file).pack(side="left")

        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(2, weight=1)

        # ── Form ──
        form = Card(self.body, padding=theme.SPACE_LG)
        form.grid(row=0, column=0, sticky="ew")
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)

        SectionTitle(form, "Thêm / sửa mục").grid(
            row=0, column=0, columnspan=4, pady=(0, theme.SPACE_SM), sticky="w")

        self.src_entry = self._entry(form, "Cụm cần thay", 0)
        self.dst_entry = self._entry(form, "Cách đọc", 2)

        opts = ctk.CTkFrame(form, fg_color="transparent")
        opts.grid(row=2, column=0, columnspan=3, pady=(theme.SPACE_SM, 0), sticky="w")
        self.whole_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts, text="Nguyên từ (không khớp bên trong từ khác)",
            variable=self.whole_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER, corner_radius=4,
        ).pack(side="left", padx=(0, theme.SPACE_MD))
        self.case_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opts, text="Phân biệt hoa/thường", variable=self.case_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER, corner_radius=4,
        ).pack(side="left")

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=2, column=3, pady=(theme.SPACE_SM, 0), sticky="e")
        Button(actions, text="✕ Bỏ chọn", variant="ghost", size="sm",
               command=self._clear_form).pack(side="left", padx=(0, theme.SPACE_SM))
        self.add_btn = Button(actions, text="＋  Thêm", variant="primary",
                              size="sm", command=self._save_entry)
        self.add_btn.pack(side="left")
        self.edit_hint = ctk.CTkLabel(
            form, text="", anchor="w", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.edit_hint.grid(row=1, column=0, columnspan=2, sticky="w")

        # ── Danh sách ──
        list_card = Card(self.body, padding=theme.SPACE_MD)
        list_card.grid(row=2, column=0, sticky="nsew", pady=(theme.SPACE_MD, 0))
        list_card.grid_rowconfigure(1, weight=1)
        list_card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(list_card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, theme.SPACE_SM))
        top.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(
            top, height=32, placeholder_text="Tìm trong từ điển…",
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.BORDER, border_width=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)
        self.count_label = ctk.CTkLabel(
            top, text="", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.count_label.grid(row=0, column=1, padx=(theme.SPACE_SM, 0))
        self.enable_switch = ctk.CTkSwitch(
            top, text="Bật từ điển", command=self._toggle_enabled,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, progress_color=theme.PRIMARY,
        )
        self.enable_switch.grid(row=0, column=2, padx=(theme.SPACE_MD, 0))
        if self._doc.get("enabled", True):
            self.enable_switch.select()
        else:
            self.enable_switch.deselect()

        self._list = ctk.CTkScrollableFrame(list_card, fg_color=theme.SURFACE)
        self._list.grid(row=1, column=0, sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.body, text="", anchor="w", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.status_label.grid(row=3, column=0, pady=(theme.SPACE_XS, 0), sticky="w")

        self._render_list()

    # ── form helper ──

    def _entry(self, parent, label: str, column: int) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent, text=label, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2, "bold"),
            text_color=theme.TEXT_DIM,
        ).grid(row=1, column=column, padx=(theme.SPACE_MD, theme.SPACE_XS),
               sticky="w")
        entry = ctk.CTkEntry(
            parent, height=34, fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.BORDER, border_width=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        entry.grid(row=1, column=column + 1, padx=(0, theme.SPACE_MD), sticky="ew")
        entry.bind("<Return>", lambda _e: self._save_entry())
        return entry

    # ── danh sách ──

    def _visible_entries(self) -> list[dict]:
        needle = self._filter.casefold()
        entries = self._doc.get("entries") or []
        if needle:
            entries = [e for e in entries
                       if needle in e["from"].casefold()
                       or needle in e["to"].casefold()]
        return entries[:_MAX_ROWS]

    def _render_list(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        entries = self._visible_entries()
        total = len(self._doc.get("entries") or [])
        self.count_label.configure(
            text=f"{len(entries)}/{total} mục" if len(entries) != total
            else f"{total} mục")
        if not entries:
            ctk.CTkLabel(
                self._list,
                text="Không có mục nào." if total == 0
                else "Không tìm thấy mục phù hợp.",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=0, padx=theme.SPACE_SM,
                   pady=theme.SPACE_LG, sticky="w")
            return

        disabled = not self._doc.get("enabled", True)
        for index, item in enumerate(entries):
            row = ctk.CTkFrame(self._list, fg_color="transparent")
            row.grid(row=index, column=0, padx=2, pady=1, sticky="ew")
            row.grid_columnconfigure(2, weight=1)

            ctk.CTkButton(
                row, text=item["from"], height=28, width=180, anchor="w",
                fg_color="transparent", hover_color=theme.HOVER_BG,
                text_color=theme.TEXT_DIM if disabled else theme.TEXT,
                corner_radius=theme.RADIUS_SM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                command=lambda it=item: self._load_entry(it),
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                row, text="→", text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=1, padx=(2, theme.SPACE_SM), sticky="w")
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
                ).grid(row=0, column=3, padx=(theme.SPACE_SM, theme.SPACE_XS))

            Button(row, text="🗑", variant="ghost", size="sm", width=30,
                   command=lambda it=item: self._delete_entry(it)).grid(
                row=0, column=4, padx=(theme.SPACE_XS, 2))

    def _on_search(self, _event=None) -> None:
        self._filter = self.search_entry.get().strip()
        self._render_list()

    # ── thao tác ──

    def _load_entry(self, item: dict) -> None:
        self._editing = item
        self._set_entry(self.src_entry, item["from"])
        self._set_entry(self.dst_entry, item["to"])
        self.whole_var.set(bool(item.get("whole_word", True)))
        self.case_var.set(bool(item.get("case_sensitive", False)))
        self.add_btn.configure(text="💾  Cập nhật")
        self.edit_hint.configure(text=f"Đang sửa: {item['from']}")

    def _clear_form(self) -> None:
        self._editing = None
        self._set_entry(self.src_entry, "")
        self._set_entry(self.dst_entry, "")
        self.whole_var.set(True)
        self.case_var.set(False)
        self.add_btn.configure(text="＋  Thêm")
        self.edit_hint.configure(text="")
        self.src_entry.focus_set()

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)

    @staticmethod
    def _same_entry(a: dict, b: dict) -> bool:
        return (a.get("from") == b.get("from")
                and bool(a.get("case_sensitive")) == bool(b.get("case_sensitive")))

    def _find_duplicate(self, source: str, entries: list[dict]) -> dict | None:
        for entry in entries:
            same = (entry["from"] == source
                    if entry.get("case_sensitive")
                    else entry["from"].casefold() == source.casefold())
            if same:
                return entry
        return None

    def _save_entry(self) -> None:
        try:
            src, dst = dictionary.validate_entry(
                self.src_entry.get(), self.dst_entry.get())
        except ValueError as exc:
            self._set_status(str(exc), theme.ERROR)
            return
        new_entry = {
            "from": src, "to": dst,
            "whole_word": bool(self.whole_var.get()),
            "case_sensitive": bool(self.case_var.get()),
        }
        entries = list(self._doc.get("entries") or [])
        if self._editing is not None:
            entries = [e for e in entries
                       if not self._same_entry(e, self._editing)]
        else:
            dup = self._find_duplicate(src, entries)
            if dup is not None:
                entries.remove(dup)
        entries.append(new_entry)
        self._doc["entries"] = entries
        self._persist()
        self._clear_form()
        self._set_status(f"Đã lưu: {src} → {dst}", theme.SUCCESS)

    def _delete_entry(self, item: dict) -> None:
        if not messagebox.askyesno(
                "Xoá mục?", f"Xoá '{item['from']}' khỏi từ điển?", parent=self):
            return
        self._doc["entries"] = [e for e in (self._doc.get("entries") or [])
                                if e["from"] != item["from"]]
        if self._editing is not None and self._same_entry(self._editing, item):
            self._clear_form()
        self._persist()
        self._set_status(f"Đã xoá: {item['from']}", theme.TEXT_DIM)

    def _toggle_enabled(self) -> None:
        self._doc["enabled"] = bool(self.enable_switch.get())
        self._persist()
        self._set_status("Đã bật từ điển." if self._doc["enabled"]
                         else "Đã tắt từ điển.", theme.SUCCESS)

    def _persist(self) -> None:
        try:
            dictionary.save(self._doc)
        except OSError as exc:
            self._set_status(f"Không ghi được từ điển: {exc}", theme.ERROR)
            return
        self.ctx._on_dictionary_changed()
        self._render_list()

    # ── nhập / xuất ──

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
            entries = {e["from"].casefold(): e
                       for e in merged.get("entries") or []}
            for entry in incoming["entries"]:
                entries[entry["from"].casefold()] = entry
            merged["entries"] = list(entries.values())
            self._doc = merged
        else:
            incoming["enabled"] = self._doc.get("enabled", True)
            self._doc = incoming
        if self._doc.get("enabled", True):
            self.enable_switch.select()
        else:
            self.enable_switch.deselect()
        self._persist()
        self._set_status(f"Đã nhập {len(incoming['entries'])} mục.",
                         theme.SUCCESS)

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

    def on_show(self) -> None:
        self._doc = dictionary.load()
        self.enable_switch.select() if self._doc.get("enabled", True) \
            else self.enable_switch.deselect()
        self._render_list()
