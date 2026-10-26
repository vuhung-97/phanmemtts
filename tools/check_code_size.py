"""Kiểm tra source trước khi obfuscate bằng PyArmor free.

PyArmor bản miễn phí giới hạn **32 768 byte cho mỗi code object** (đo trên
bytecode `co_code`, đã kiểm chứng thực tế với bản build của dự án).
Đồng thời chặn file có BOM (PyArmor không parse được) và lỗi cú pháp.

    .venv\\Scripts\\python.exe tools\\check_code_size.py build\\src
"""

from __future__ import annotations

import argparse
import marshal
import sys
import types
from pathlib import Path

LIMIT = 32_768
BOM = b"\xef\xbb\xbf"


def _walk(code: types.CodeType):
    yield code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from _walk(const)


def biggest_code(code: types.CodeType) -> tuple[int, str]:
    """(số byte bytecode lớn nhất, tên hàm) trong một module."""
    best = (0, "<module>")
    for item in _walk(code):
        size = len(item.co_code)
        if size > best[0]:
            best = (size, item.co_name)
    return best


def scan(root: Path, limit: int) -> int:
    failures = 0
    rows: list[tuple[int, int, int, Path, str, str]] = []

    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        raw = path.read_bytes()
        problem = ""
        if raw.startswith(BOM):
            problem = "BOM UTF-8 (PyArmor không đọc được)"
            failures += 1
        try:
            code = compile(raw.decode("utf-8-sig"), str(path), "exec")
        except SyntaxError as exc:
            print(f"[LOI] {path.relative_to(root)}: {exc}")
            failures += 1
            continue

        code_bytes, owner = biggest_code(code)
        marshal_size = len(marshal.dumps(code))
        rows.append((code_bytes, marshal_size, len(raw), path, owner, problem))
        if code_bytes > limit:
            failures += 1

    rows.sort(reverse=True)
    print(f"{'bytecode':>9}  {'marshal':>9}  {'source':>8}  file (hàm lớn nhất)")
    print("-" * 82)
    for code_bytes, marshal_size, src_size, path, owner, problem in rows[:10]:
        flag = "  <-- VUOT" if code_bytes > limit else ""
        note = f"  [{problem}]" if problem else ""
        print(f"{code_bytes:>9,}  {marshal_size:>9,}  {src_size:>8,}  "
              f"{path.relative_to(root)} ({owner}){flag}{note}")

    over = [row for row in rows if row[0] > limit]
    if over:
        print(f"\n[LOI] {len(over)} file có code object vượt {limit:,} byte.")
        print("      Tách hàm/module đó ra file nhỏ hơn.")
    if failures:
        print(f"\n[LOI] Tổng {failures} vấn đề (BOM / vượt giới hạn / syntax).")
        return 1

    biggest = rows[0][0] if rows else 0
    print(f"\n[OK] {len(rows)} file, code object lớn nhất {biggest:,} byte "
          f"(giới hạn {limit:,}).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra kích thước code object")
    parser.add_argument("src", nargs="?", default="build/src")
    parser.add_argument("--limit", type=int, default=LIMIT)
    args = parser.parse_args()

    root = Path(args.src)
    if not root.is_dir():
        print(f"[LOI] Không thấy thư mục: {root}")
        return 1
    return scan(root, args.limit)


if __name__ == "__main__":
    sys.exit(main())
