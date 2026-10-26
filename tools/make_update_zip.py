"""Tạo gói cập nhật nhỏ (chỉ file đã đổi) từ 2 manifest.

    .venv\\Scripts\\python.exe tools\\make_update_zip.py --dist dist\\<APP>
    .venv\\Scripts\\python.exe tools\\make_update_zip.py --dist dist\\<APP> --prev build\\manifests\\3.3.0.json

Điều kiện: cùng phiên bản Python/PyArmor (khác -> cần build full).
Nếu file .exe thay đổi, nó được đưa vào payload (gói ~30 MB) — vẫn nhỏ hơn
nhiều so với gửi cả bộ cài ~1 GB.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATE_SCRIPT = ROOT / "tools" / "update_script"
STAGE_ROOT = ROOT / "build" / "_update_stage"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_prev(current: dict, prev_arg: str, archive: Path) -> Path | None:
    if prev_arg and prev_arg != "auto":
        path = Path(prev_arg)
        return path if path.is_file() else None

    candidates = []
    if archive.is_dir():
        for path in archive.glob("*.json"):
            try:
                data = load_json(path)
            except (OSError, ValueError):
                continue
            if data.get("version") == current.get("version"):
                continue
            if data.get("app") != current.get("app"):
                continue
            candidates.append((path.stat().st_mtime, path))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Tao goi cap nhat")
    parser.add_argument("--dist", default="dist/PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3")
    parser.add_argument("--prev", default="auto", help="manifest ban truoc (mac dinh: auto)")
    parser.add_argument("--out", default="")
    parser.add_argument("--archive", default="build/manifests")
    args = parser.parse_args()

    dist = Path(args.dist)
    manifest_path = dist / "manifest.json"
    if not manifest_path.is_file():
        print(f"[LOI] Chua co {manifest_path} — chay make_manifest.py truoc.")
        return 1
    current = load_json(manifest_path)

    prev_path = find_prev(current, args.prev, Path(args.archive))
    if prev_path is None:
        print("[i] Chua co manifest ban truoc -> bo qua tao goi cap nhat.")
        return 0

    prev = load_json(prev_path)
    old_version = prev.get("version", "?")
    new_version = current.get("version", "?")

    if (prev.get("python") != current.get("python")
            or prev.get("pyarmor") != current.get("pyarmor")):
        print("[LOI] Python/PyArmor thay đổi -> phải build full.")
        return 2

    prev_files = prev.get("files", {})
    cur_files = current.get("files", {})

    changed = sorted(rel for rel, info in cur_files.items()
                     if prev_files.get(rel, {}).get("sha256") != info["sha256"])
    deleted = sorted(rel for rel in prev_files if rel not in cur_files)
    runtime = sorted(rel for rel in cur_files
                     if rel.startswith("pyarmor_runtime_000000/"))

    payload = sorted(set(changed) | set(runtime))
    if not payload and not deleted:
        print(f"[i] Khong co thay doi so voi {old_version}.")
        return 0

    exe_name = current.get("exe", {}).get("name", "")
    if exe_name and exe_name in payload:
        print(f"[i] File .exe thay doi -> gói cập nhật sẽ lớn hơn (~"
              f"{current['files'][exe_name]['size'] / (1024 * 1024):.0f} MB).")

    stage = STAGE_ROOT / f"capnhat_{new_version}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    for rel in payload:
        src = dist / rel
        dst = stage / "payload" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    if deleted:
        (stage / "delete.txt").write_text("\n".join(deleted) + "\n", encoding="utf-8")

    (stage / "manifest_update.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    for name in ("capnhat.bat", "capnhat.ps1"):
        src = UPDATE_SCRIPT / name
        if not src.is_file():
            print(f"[LOI] Thieu {src}")
            return 1
        shutil.copy2(src, stage / name)

    out = Path(args.out) if args.out else ROOT / "build" / f"update_{new_version}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                arc = Path(stage.name) / path.relative_to(stage)
                zf.write(path, arc.as_posix())

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"[OK] {out}  ({size_mb:.2f} MB)")
    print(f"     {old_version} -> {new_version}: {len(payload)} file payload, "
          f"{len(deleted)} file xoa")
    for rel in payload[:8]:
        print(f"       + {rel}")
    if len(payload) > 8:
        print(f"       ... (+{len(payload) - 8})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
