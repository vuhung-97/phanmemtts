from __future__ import annotations

from pathlib import Path

from docx import Document


def read_document(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _read_docx(path)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Định dạng không được hỗ trợ: {suffix}")


def _read_docx(path: Path) -> str:
    document = Document(str(path))
    parts: list[str] = [p.text for p in document.paragraphs]
    return "\n".join(parts)
