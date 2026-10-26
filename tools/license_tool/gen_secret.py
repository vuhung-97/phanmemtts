"""Sinh secret 32 byte cho hệ thống mã kích hoạt.

Chạy MỘT lần duy nhất trên máy owner:

    .venv\\Scripts\\python.exe tools\\license_tool\\gen_secret.py

File được ghi vào tools/license_tool/keys/license_secret.bin (đã gitignore).
Mất file này = không cấp được mã mới cho bản phát hành hiện tại, nên phải
backup ngay (USB + password manager).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECRET_PATH = ROOT / "tools" / "license_tool" / "keys" / "license_secret.bin"

SECRET_LEN = 32


def main() -> int:
    parser = argparse.ArgumentParser(description="Sinh secret cho mã kích hoạt")
    parser.add_argument("--force", action="store_true",
                        help="Ghi đè secret đã có (nguy hiểm: vô hiệu mọi mã đã cấp)")
    args = parser.parse_args()

    if SECRET_PATH.exists() and not args.force:
        print(f"[!] Đã có secret: {SECRET_PATH}")
        print("    Không ghi đè. Đổi secret sẽ làm vô hiệu toàn bộ mã đã cấp.")
        print("    Nếu thật sự muốn tạo mới, chạy lại với --force.")
        return 1

    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = os.urandom(SECRET_LEN)
    SECRET_PATH.write_bytes(data)

    print(f"[+] Đã ghi {SECRET_PATH} ({SECRET_LEN} byte)")
    fingerprint = hashlib.sha256(data).hexdigest()[:16]
    print(f"    fingerprint (sha256 secret, 16 hex) = {fingerprint}")
    print("    (Không in 4 mảnh ra màn hình để tránh lộ qua ảnh chụp/log.)")
    print()
    print("[!] BACKUP NGAY file này (USB + password manager).")
    print("    Mất secret = không cấp được mã mới cho bản phát hành hiện tại.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
