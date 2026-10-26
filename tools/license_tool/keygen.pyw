"""Tool cấp mã kích hoạt — chạy trên máy owner.

Mở bằng:  tools\\license_tool\\keygen.bat
(hoặc:    .venv\\Scripts\\pythonw.exe tools\\license_tool\\keygen.pyw)
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import ledger  # noqa: E402
from core.licensing import shortcode  # noqa: E402

PAD = {"padx": 12, "pady": 4}


def _date_text(day_index: int | None) -> str:
    if day_index is None:
        return "Vĩnh viễn"
    return (shortcode.EPOCH + timedelta(days=int(day_index))).strftime("%d/%m/%Y")


class KeygenApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cấp mã kích hoạt — Phần mềm chuyển văn bản thành giọng nói")
        self.geometry("760x600")
        self.minsize(700, 560)

        self.var_machine = tk.StringVar()
        self.var_kind = tk.StringVar(value="30")
        self.var_days = tk.IntVar(value=90)
        self.var_customer = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_note = tk.StringVar()
        self.var_code = tk.StringVar()
        self.var_expiry = tk.StringVar(value="—")
        self.var_status = tk.StringVar(value="")
        self.var_count = tk.StringVar(value="")

        self._last: tuple[str, str, int, int | None, shortcode.ShortCode] | None = None

        self._build()
        self._check_secret()
        self._refresh_count()
        self.bind("<Return>", lambda _e: self._generate())
        self.after(200, lambda: self.entry_machine.focus_set())

    # ── UI ──

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        # Mã máy
        box = ttk.LabelFrame(outer, text=" 1. Mã máy của khách ", padding=10)
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Mã máy (10 ký tự)").grid(row=0, column=0, sticky="w")
        self.entry_machine = ttk.Entry(box, textvariable=self.var_machine,
                                       font=("Consolas", 12))
        self.entry_machine.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(box, text="Dán", width=7, command=self._paste).grid(
            row=0, column=2)

        # Loại mã
        box2 = ttk.LabelFrame(outer, text=" 2. Loại mã ", padding=10)
        box2.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        for i, (value, label) in enumerate((("7", "7 ngày"),
                                            ("30", "30 ngày"),
                                            ("lifetime", "Vĩnh viễn"),
                                            ("custom", "Tuỳ chỉnh"))):
            ttk.Radiobutton(box2, text=label, value=value,
                            variable=self.var_kind,
                            command=self._kind_changed).grid(
                row=0, column=i, padx=(0, 14), sticky="w")

        ttk.Spinbox(box2, from_=1, to=shortcode.MAX_CUSTOM_DAYS, width=6,
                    textvariable=self.var_days).grid(row=0, column=4, padx=(4, 4))
        ttk.Label(box2, text="ngày").grid(row=0, column=5, sticky="w")
        self.spin_days = box2.grid_slaves(row=0, column=4)[0]
        self._kind_changed()

        # Khách
        box3 = ttk.LabelFrame(outer, text=" 3. Thông tin khách (tuỳ chọn) ",
                              padding=10)
        box3.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        box3.columnconfigure(1, weight=1)
        box3.columnconfigure(3, weight=1)
        ttk.Label(box3, text="Tên khách").grid(row=0, column=0, sticky="w")
        ttk.Entry(box3, textvariable=self.var_customer).grid(
            row=0, column=1, sticky="ew", padx=(6, 12))
        ttk.Label(box3, text="SĐT").grid(row=0, column=2, sticky="w")
        ttk.Entry(box3, textvariable=self.var_phone).grid(
            row=0, column=3, sticky="ew", padx=(6, 0))
        ttk.Label(box3, text="Ghi chú").grid(row=1, column=0, sticky="w",
                                            pady=(6, 0))
        ttk.Entry(box3, textvariable=self.var_note).grid(
            row=1, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(6, 0))

        ttk.Button(outer, text="Tạo mã kích hoạt", command=self._generate).grid(
            row=3, column=0, pady=10, sticky="ew")

        # Kết quả
        box4 = ttk.LabelFrame(outer, text=" 4. Mã kích hoạt ", padding=10)
        box4.grid(row=4, column=0, sticky="ew")
        box4.columnconfigure(1, weight=1)

        ttk.Label(box4, text="Mã (15 ký tự)").grid(row=0, column=0, sticky="w")
        self.entry_code = ttk.Entry(box4, textvariable=self.var_code,
                                    font=("Consolas", 14), state="readonly")
        self.entry_code.grid(row=0, column=1, sticky="ew", padx=8)
        self.btn_copy = ttk.Button(box4, text="Sao chép", width=10,
                                   command=self._copy, state="disabled")
        self.btn_copy.grid(row=0, column=2)

        ttk.Label(box4, text="Hạn dùng").grid(row=1, column=0, sticky="w",
                                            pady=(8, 0))
        ttk.Label(box4, textvariable=self.var_expiry,
                  font=("Segoe UI", 10, "bold")).grid(
            row=1, column=1, sticky="w", padx=8, pady=(8, 0))

        actions = ttk.Frame(box4)
        actions.grid(row=2, column=0, columnspan=3, sticky="e", pady=(10, 0))
        self.btn_save = ttk.Button(actions, text="Lưu file .lic…",
                                   command=self._save_lic, state="disabled")
        self.btn_save.pack(side="left", padx=(0, 8))
        self.btn_record = ttk.Button(actions, text="Ghi vào sổ",
                                     command=self._record, state="disabled")
        self.btn_record.pack(side="left")

        # Trạng thái + sổ key
        bottom = ttk.Frame(outer)
        bottom.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.var_status, foreground="#1f5f3f").grid(
            row=0, column=0, sticky="w")
        ttk.Label(bottom, textvariable=self.var_count, foreground="#666666").grid(
            row=0, column=1, sticky="e", padx=(0, 10))
        ttk.Button(bottom, text="Xem sổ key", command=self._show_ledger).grid(
            row=0, column=2, sticky="e")

    # ── Logic ──

    def _check_secret(self) -> None:
        if common.SECRET_PATH.exists():
            return
        self.var_status.set("Chưa có secret — hãy chạy gen_secret.py trước.")
        messagebox.showerror(
            "Thiếu secret",
            "Không thấy file:\n"
            f"{common.SECRET_PATH}\n\n"
            "Chạy lệnh sau ở thư mục dự án:\n"
            r"  .venv\Scripts\python.exe tools\license_tool\gen_secret.py",
            parent=self,
        )

    def _kind_changed(self) -> None:
        state = "normal" if self.var_kind.get() == "custom" else "disabled"
        try:
            self.spin_days.configure(state=state)
        except Exception:
            pass

    def _paste(self) -> None:
        try:
            text = self.clipboard_get()
        except Exception:
            return
        self.var_machine.set(text.strip())
        self.entry_machine.focus_set()

    def _generate(self) -> None:
        try:
            machine = common.normalize_machine(self.var_machine.get())
        except ValueError as exc:
            messagebox.showerror("Mã máy không hợp lệ", str(exc), parent=self)
            return
        self.var_machine.set(common.format_machine(machine))

        kind = common.KIND_CHOICES[self.var_kind.get()]
        days = int(self.var_days.get()) if kind == shortcode.KIND_CUSTOM else None

        try:
            key = common.load_key()
            code, sc = common.create_code(machine, kind, days=days, key=key)
        except Exception as exc:
            messagebox.showerror("Không tạo được mã", str(exc), parent=self)
            return

        self._last = (code, machine, kind, days, sc)
        self.var_code.set(code)
        self.var_expiry.set(common.expiry_text(sc))
        self.btn_copy.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.btn_record.configure(state="normal")

        old = ledger.by_machine(machine)
        note = f" (máy này đã được cấp {len(old)} mã trước đó)" if old else ""
        self.var_status.set(
            f"Đã tạo mã {common.kind_text(kind, days)} — hạn {common.expiry_text(sc)}.{note}")

    def _copy(self) -> None:
        code = self.var_code.get()
        if not code:
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        self.var_status.set("Đã sao chép mã kích hoạt.")

    def _save_lic(self) -> None:
        if not self._last:
            return
        code, machine, kind, days, sc = self._last
        path = filedialog.asksaveasfilename(
            parent=self, title="Lưu file mã kích hoạt",
            defaultextension=".lic",
            initialfile=f"{common.format_machine(machine)}.lic",
            filetypes=[("Mã kích hoạt", "*.lic"), ("Tất cả", "*.*")],
        )
        if not path:
            return
        payload = {
            "type": "ppmt-key",
            "ver": 1,
            "code": code,
            "machine": common.format_machine(machine),
            "issued": date.today().isoformat(),
            "kind": common.kind_text(kind, days),
            "expiry": common.expiry_text(sc),
            "note": self.var_note.get().strip(),
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        self.var_status.set(f"Đã lưu: {path}")

    def _record(self) -> None:
        if not self._last:
            return
        code, machine, kind, days, sc = self._last
        record_id = ledger.add(
            code=code,
            machine=machine,
            kind=kind,
            days=int(days or 0),
            issued_day=shortcode.day_index(shortcode.utc_today()),
            expiry_day=None if sc.is_lifetime else sc.expiry_day,
            customer=self.var_customer.get().strip(),
            phone=self.var_phone.get().strip(),
            note=self.var_note.get().strip(),
        )
        self.btn_record.configure(state="disabled")
        self.var_status.set(f"Đã ghi vào sổ key #{record_id}.")
        self._refresh_count()

    def _refresh_count(self) -> None:
        try:
            self.var_count.set(f"Sổ key: {ledger.count()} bản ghi")
        except Exception:
            self.var_count.set("Sổ key: —")

    # ── Sổ key ──

    def _show_ledger(self) -> None:
        LedgerWindow(self)


class LedgerWindow(tk.Toplevel):
    COLUMNS = (("id", "ID", 50), ("machine", "Mã máy", 120),
               ("kind", "Loại", 110), ("expiry", "Hạn", 90),
               ("customer", "Khách", 150), ("phone", "SĐT", 100),
               ("created", "Tạo lúc", 140))

    def __init__(self, master: KeygenApp) -> None:
        super().__init__(master)
        self.title("Sổ key đã cấp")
        self.geometry("820x460")
        self.transient(master)
        self._master = master
        self._build()
        self._load()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=(10, 8))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text="100 bản ghi gần nhất").grid(row=0, column=0, sticky="w")
        ttk.Button(top, text="Làm mới", command=self._load).grid(row=0, column=1,
                                                                sticky="e")

        frame = ttk.Frame(self)
        frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(frame, columns=[c[0] for c in self.COLUMNS],
                                 show="headings", height=16)
        for key, label, width in self.COLUMNS:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

    def _load(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            rows = ledger.recent(100)
        except Exception as exc:
            messagebox.showerror("Không đọc được sổ key", str(exc), parent=self)
            return
        for row in rows:
            kind = common.kind_text(int(row["kind"]), int(row["days"] or 0))
            created = date.fromtimestamp(int(row["created_at"])).strftime(
                "%d/%m/%Y %H:%M")
            self.tree.insert("", "end", values=(
                row["id"],
                common.format_machine(row["machine"]),
                kind,
                _date_text(row["expiry_day"]),
                row["customer"] or "",
                row["phone"] or "",
                created,
            ))


def main() -> int:
    app = KeygenApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
