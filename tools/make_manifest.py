"""Sinh manifest.json (sha256 từng file) cho thư mục phát hành.

Chỉ liệt kê file thuộc gói cập nhật được (code, docs, runtime); bỏ
`_internal/`, `models/`, `backup/`, file exe và chính manifest.

    .venv\\Scripts\\python.exe tools\\make_manifest.py --dist dist\\<APP> --archive build\\manifests
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKIP_DIRS = {"_internal", "models", "backup", "__pycache__"}
SKIP_NAMES = {"manifest.json", "manifest_update.json"}
CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _pyarmor_version() -> str:
    try:
        from importlib.metadata import version

        return version("pyarmor")
    except Exception:
        return "?"


def build_manifest(dist: Path) -> dict:
    import version as app_version

    files: dict[str, dict] = {}
    for path in sorted(dist.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(dist)
        if rel.parts and rel.parts[0] in SKIP_DIRS:
            continue
        if path.name in SKIP_NAMES:
            continue
        files[rel.as_posix()] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }

    exes = sorted(dist.glob("*.exe"))
    exe = {
        "name": exes[0].name,
        "sha256": sha256_file(exes[0]),
        "size": exes[0].stat().st_size,
    } if len(exes) == 1 else {}

    return {
        "app": dist.name,
        "version": app_version.__version__,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pyarmor": _pyarmor_version(),
        "key_format": 1,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exe": exe,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sinh manifest.json")
    parser.add_argument("--dist", default="dist/PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3")
    parser.add_argument("--archive", default="build/manifests",
                        help="thu muc luu ban manifest theo phien ban (dung cho update zip)")
    args = parser.parse_args()

    dist = Path(args.dist)
    if not dist.is_dir():
        print(f"[LOI] Khong thay thu muc: {dist}")
        return 1
    if not list(dist.glob("*.exe")):
        print(f"[LOI] Khong thay file .exe trong {dist}")
        return 1

    manifest = build_manifest(dist)
    target = dist / "manifest.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    total = sum(item["size"] for item in manifest["files"].values())
    print(f"[OK] {target}")
    print(f"     {len(manifest['files'])} file ({total / 1024:.0f} KB), "
          f"version {manifest['version']}, python {manifest['python']}, "
          f"pyarmor {manifest['pyarmor']}")

    if args.archive:
        archive = Path(args.archive)
        archive.mkdir(parents=True, exist_ok=True)
        copy = archive / f"{manifest['version']}.json"
        copy.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        print(f"     luu ban: {copy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
