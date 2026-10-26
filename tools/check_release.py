"""Quét thư mục phát hành để chặn lọt secret / source chưa obfuscate.

    .venv\\Scripts\\python.exe tools\\check_release.py --dist dist\\<APP>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FORBIDDEN_DIRS = {"keys", "__pycache__", ".git"}
FORBIDDEN_NAMES = {"license_secret.bin", "issued.sqlite"}
FORBIDDEN_SUFFIX = {".key", ".pem", ".lic"}
SCAN_PY_DIRS = ("core", "engine", "audio", "ui")
SKIP_TREES = {"_internal", "models", "backup"}
PYARMOR_MARK = b"Pyarmor"


def scan(dist: Path) -> int:
    problems: list[str] = []
    warnings: list[str] = []

    for path in dist.rglob("*"):
        rel = path.relative_to(dist)
        if rel.parts and rel.parts[0] in SKIP_TREES:
            continue

        if path.is_dir():
            if path.name in FORBIDDEN_DIRS:
                problems.append(f"thu muc cam: {rel.as_posix()}")
            continue

        if path.name in FORBIDDEN_NAMES:
            problems.append(f"file cam: {rel.as_posix()}")
        if path.suffix.lower() in FORBIDDEN_SUFFIX:
            problems.append(f"file cam: {rel.as_posix()}")

    # Source .py trong các gói app phải đã obfuscate (có header Pyarmor).
    targets = [dist / "version.py"]
    for name in SCAN_PY_DIRS:
        folder = dist / name
        if folder.is_dir():
            targets.extend(folder.rglob("*.py"))
    for path in targets:
        if not path.is_file():
            continue
        head = path.read_bytes()[:512]
        if PYARMOR_MARK not in head:
            problems.append(f"chua obfuscate: {path.relative_to(dist).as_posix()}")

    runtime = dist / "pyarmor_runtime_000000" / "pyarmor_runtime.pyd"
    if not runtime.is_file():
        problems.append("thieu pyarmor_runtime_000000/pyarmor_runtime.pyd")

    if not (dist / "manifest.json").is_file():
        warnings.append("thieu manifest.json (chay tools/make_manifest.py)")

    exes = list(dist.glob("*.exe"))
    if len(exes) != 1:
        warnings.append(f"so file .exe o goc = {len(exes)} (mong doi 1)")

    for line in warnings:
        print(f"[CANH BAO] {line}")
    for line in problems:
        print(f"[LOI] {line}")

    if problems:
        print(f"\n[LOI] {len(problems)} van de — dung build de gui khach.")
        return 1
    print(f"[OK] Khong thay secret/source chua obfuscate trong {dist}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Quet thu muc phat hanh")
    parser.add_argument("--dist", default="dist/PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3")
    args = parser.parse_args()

    dist = Path(args.dist)
    if not dist.is_dir():
        print(f"[LOI] Khong thay thu muc: {dist}")
        return 1
    return scan(dist)


if __name__ == "__main__":
    sys.exit(main())
