"""Kiểm tra bản đóng gói KeygenTTS trước khi mang đi dùng.

    .venv\\Scripts\\python.exe tools\\license_tool\\check_release.py
    .venv\\Scripts\\python.exe tools\\license_tool\\check_release.py --selftest build\\keygen_selftest.txt

Chặn: thiếu exe / thiếu secret / secret bị nhúng trong exe.
Nếu có file selftest: so mã do exe sinh với mã tính trong repo (cùng secret).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import common  # noqa: E402
from core.licensing import shortcode  # noqa: E402

DIST = ROOT / "dist" / "KeygenTTS"
ok = True


def check(name: str, condition: bool, detail: str = "") -> None:
    global ok
    print(f"[{'OK ' if condition else 'LOI'}] {name}" + (f" — {detail}" if detail else ""))
    ok = ok and bool(condition)


def main() -> int:
    dist = DIST
    args = sys.argv[1:]
    if args and not args[0].startswith("--"):
        dist = Path(args[0])

    exe = dist / "KeygenTTS.exe"
    secret = dist / "keys" / "license_secret.bin"

    check("có KeygenTTS.exe", exe.is_file())
    check("có keys/license_secret.bin", secret.is_file())

    if exe.is_file() and secret.is_file():
        payload = exe.read_bytes()
        raw = secret.read_bytes()
        check("secret không bị nhúng trong exe", raw not in payload,
              f"exe {len(payload) / 1024 / 1024:.1f} MB")

    selftest = dist / "keygen_selftest.txt"
    if "--selftest" in args:
        index = args.index("--selftest")
        selftest = Path(args[index + 1]) if index + 1 < len(args) else selftest

    if selftest.is_file() and secret.is_file():
        first = selftest.read_text(encoding="utf-8").splitlines()
        code = first[0].strip() if first else ""
        try:
            key = common.load_key(secret)
            expected, _ = common.create_code("00000-00000",
                                             shortcode.KIND_MONTH, key=key)
        except Exception as exc:
            check("đọc secret để đối chiếu", False, str(exc))
            expected = ""
        check("exe sinh mã khớp repo", code == expected, f"{code} vs {expected}")

    print("\nKẾT QUẢ:", "OK" if ok else "CÓ LỖI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
