"""Ghi 4 mảnh secret thật vào cây source tạm trước khi obfuscate.

    .venv\\Scripts\\python.exe tools\\inject_secret.py build\\src

Sau bước này `build/src/core/licensing/_k1..4.py` chứa mảnh thật; cây
`build/src` phải bị xoá sau khi build xong (nằm trong .gitignore).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATH = ROOT / "tools" / "license_tool" / "keys" / "license_secret.bin"

TEMPLATE = '''"""Mảnh {index}/4 của secret ký mã kích hoạt (giá trị thật, sinh lúc build).

File này được tools/inject_secret.py sinh tự động vào cây source tạm;
KHÔNG commit và KHÔNG sửa tay.
"""

PART = bytes.fromhex("{hex}")
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject secret vào cây build")
    parser.add_argument("src", nargs="?", default="build/src",
                        help="thư mục source tạm (mặc định: build/src)")
    args = parser.parse_args()

    src = (ROOT / args.src).resolve() if not Path(args.src).is_absolute() else Path(args.src)
    if not src.is_dir():
        print(f"[LOI] Không thấy thư mục source: {src}")
        return 1
    if not SECRET_PATH.is_file():
        print(f"[LOI] Không thấy secret: {SECRET_PATH}")
        print("      Chạy trước: python tools\\license_tool\\gen_secret.py")
        return 1

    data = SECRET_PATH.read_bytes()
    if len(data) != 32:
        print(f"[LOI] Secret phải đúng 32 byte (đang {len(data)}).")
        return 1

    target_dir = src / "core" / "licensing"
    if not target_dir.is_dir():
        print(f"[LOI] Không thấy {target_dir}")
        return 1

    for i in range(4):
        part = data[i * 8:(i + 1) * 8]
        path = target_dir / f"_k{i + 1}.py"
        path.write_text(
            TEMPLATE.format(index=i + 1, hex=part.hex().upper()),
            encoding="utf-8",
        )

    key = hashlib.sha256(b"PPMTTS|key|v1|" + data).digest()
    print(f"[+] Đã inject 4 mảnh vào {target_dir}")
    print(f"    fingerprint = {hashlib.sha256(key).hexdigest()[:16]} (so sánh giữa các build)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
