"""Probe P5: kiểm tra bản phát hành đã obfuscate (dist/<APP>).

    .venv\\Scripts\\python.exe packaging\\probe_obfuscated_build.py
    .venv\\Scripts\\python.exe packaging\\probe_obfuscated_build.py build\\dist_p4\\<APP>

Kiểm tra:
  1. manifest.json tồn tại và sha256 của toàn bộ file khớp.
  2. core/engine/audio/ui/version.py đã obfuscate (header Pyarmor).
  3. Không có secret / key / sổ key / __pycache__ / .py chưa obfuscate.
  4. Có models/ (hf_cache) để chạy offline.
  5. Exe khởi động được và tạo cửa sổ đúng tiêu đề.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import version  # noqa: E402

APP_NAME = "PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3"
DEFAULT_DIST = ROOT / "dist" / APP_NAME
SKIP_DIRS = {"_internal", "models", "backup", "__pycache__"}
ok = True


def check(name: str, condition: bool, detail: str = "") -> None:
    global ok
    print(f"[{'OK ' if condition else 'LOI'}] {name}" + (f" — {detail}" if detail else ""),
          flush=True)
    ok = ok and bool(condition)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_manifest(dist: Path) -> None:
    path = dist / "manifest.json"
    if not path.is_file():
        check("có manifest.json", False)
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    check("manifest: phiên bản khớp version.py",
          manifest.get("version") == version.__version__,
          f"{manifest.get('version')} vs {version.__version__}")

    bad = []
    for rel, info in manifest.get("files", {}).items():
        target = dist / rel
        if not target.is_file():
            bad.append(f"thiếu {rel}")
        elif sha256_file(target) != info["sha256"]:
            bad.append(f"sai hash {rel}")
    check(f"manifest: {len(manifest.get('files', {}))} file khớp sha256",
          not bad, "; ".join(bad[:3]))


def check_obfuscated(dist: Path) -> None:
    targets = [dist / "version.py"]
    for name in ("core", "engine", "audio", "ui"):
        folder = dist / name
        if folder.is_dir():
            targets.extend(folder.rglob("*.py"))
    plain = [p for p in targets if p.is_file()
             and b"Pyarmor" not in p.read_bytes()[:512]]
    check(f"code đã obfuscate ({len(targets)} file)", not plain,
          ", ".join(str(p.relative_to(dist)) for p in plain[:3]))


def check_secrets(dist: Path) -> None:
    forbidden = []
    for path in dist.rglob("*"):
        rel = path.relative_to(dist)
        if rel.parts and rel.parts[0] in SKIP_DIRS:
            continue
        if path.name in {"license_secret.bin", "issued.sqlite"}:
            forbidden.append(rel.as_posix())
        if path.suffix.lower() in {".key", ".lic", ".pem"}:
            forbidden.append(rel.as_posix())
        if path.name == "__pycache__":
            forbidden.append(rel.as_posix())
    check("không có secret/key/sổ key/__pycache__", not forbidden,
          ", ".join(forbidden[:5]))


def check_models(dist: Path) -> None:
    models = dist / "models"
    has_cache = (models / "vieneu" / "hf_cache").is_dir()
    has_config = (models / "voice_config.json").is_file()
    check("có models/hf_cache + voice_config.json", has_cache and has_config,
          f"hf_cache={has_cache} config={has_config}")


def check_launch(dist: Path) -> None:
    exe = dist / f"{APP_NAME}.exe"
    if not exe.is_file():
        check("có file exe", False)
        return
    proc = subprocess.Popen([str(exe)], cwd=str(dist))
    title = f"{version.__app_name__} - v{version.__version__}"
    found = False
    try:
        for _ in range(40):
            time.sleep(0.75)
            hwnd = ctypes.windll.user32.FindWindowW(None, title)
            if hwnd and ctypes.windll.user32.IsWindowVisible(hwnd):
                found = True
                break
            if proc.poll() is not None:
                break
        check("exe khởi động và mở cửa sổ", found,
              "không thấy cửa sổ" if not found else "")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    dist = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIST
    if not dist.is_dir():
        print(f"[LOI] Không thấy thư mục phát hành: {dist}")
        return 1

    print(f"Dist: {dist}")
    print(f"Version: {version.__version__}\n")

    check_manifest(dist)
    check_obfuscated(dist)
    check_secrets(dist)
    check_models(dist)
    check_launch(dist)

    print("\nKẾT QUẢ:", "OK" if ok else "CÓ LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
