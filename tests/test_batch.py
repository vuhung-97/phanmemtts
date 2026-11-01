"""Kiểm thử tách phần hàng loạt theo marker [P1]/[P2]."""

from __future__ import annotations

import zipfile

from core.batch import (part_filename, parse_batch, sanitize_filename,
                        write_zip)


def test_no_marker_returns_single_part():
    parts = parse_batch("Câu một. Câu hai.")
    assert len(parts) == 1
    assert parts[0].marker == ""
    assert parts[0].label == "Toàn bộ"
    assert parts[0].sentence_count == 2


def test_parses_each_marker_as_part():
    text = "[P1] Phần một.\nNội dung.\n[P2] Phần hai."
    parts = parse_batch(text)
    assert [p.marker for p in parts] == ["P1", "P2"]
    assert parts[0].text == "Phần một.\nNội dung."
    assert parts[1].text == "Phần hai."


def test_marker_must_be_at_line_start():
    text = "Câu có [P1] giữa dòng.\n[P2] Phần hai."
    parts = parse_batch(text)
    # [P1] giữa dòng KHÔNG phải marker -> phần đầu thành P0
    assert [p.marker for p in parts] == ["P0", "P2"]
    assert parts[0].text == "Câu có [P1] giữa dòng."
    assert parts[1].text == "Phần hai."


def test_text_before_first_marker_becomes_p0():
    text = "Lời dẫn.\n[P1] Phần một."
    parts = parse_batch(text)
    assert [p.marker for p in parts] == ["P0", "P1"]
    assert parts[0].text == "Lời dẫn."


def test_empty_parts_are_dropped():
    parts = parse_batch("[P1] A.\n[P2]\n[P3] B.")
    assert [p.marker for p in parts] == ["P1", "P3"]


def test_lowercase_and_wide_numbers():
    parts = parse_batch("[p12] Mười hai.\n[P003] Ba.")
    assert [p.marker for p in parts] == ["P12", "P003"]


def test_crlf_and_blank_lines():
    parts = parse_batch("[P1]\r\nDòng một.\r\nDòng hai.\r\n[P2]\r\nHai.")
    assert len(parts) == 2
    assert "Dòng một." in parts[0].text


def test_empty_text():
    assert parse_batch("") == []
    assert parse_batch("   \n\n ") == []


def test_counts():
    part = parse_batch("[P1] Một. Hai. Ba.")[0]
    assert part.char_count == len("Một. Hai. Ba.")
    assert part.sentence_count == 3


# ── Tên tệp ──

def test_sanitize_removes_illegal_chars():
    assert sanitize_filename('bai:1/TEST?*') == "bai_1_TEST__"
    assert sanitize_filename("   ") == "audio"
    assert sanitize_filename("CON") == "_CON"


def test_sanitize_keeps_vietnamese():
    assert sanitize_filename("Bài đọc số 1") == "Bài đọc số 1"


def test_part_filename_uses_marker():
    part = parse_batch("[P1] Xin chào.")[0]
    assert part_filename(part, "bai", ".mp3") == "bai_P1.mp3"
    assert part_filename(part, "", "wav") == "P1.wav"


def test_part_filename_without_marker():
    part = parse_batch("Xin chào.")[0]
    assert part_filename(part, "bai", ".mp3") == "bai.mp3"


def test_part_filename_deduplicates():
    part = parse_batch("[P1] Xin chào.")[0]
    used: set[str] = set()
    first = part_filename(part, "bai", ".mp3", used)
    second = part_filename(part, "bai", ".mp3", used)
    assert (first, second) == ("bai_P1.mp3", "bai_P1_2.mp3")


def test_write_zip(tmp_path):
    one = tmp_path / "a.mp3"
    two = tmp_path / "b.mp3"
    one.write_bytes(b"a")
    two.write_bytes(b"b")
    archive = write_zip([one, two], tmp_path / "out.zip")
    assert archive.exists()
    with zipfile.ZipFile(archive) as zf:
        assert sorted(zf.namelist()) == ["a.mp3", "b.mp3"]


# ── Đọc kịch bản từ .docx / .txt ──

def test_batch_from_docx(tmp_path):
    from docx import Document

    from core.document_reader import read_document

    document = Document()
    document.add_paragraph("[P1] Phần một.")
    document.add_paragraph("Nội dung phần một.")
    document.add_paragraph("[P2] Phần hai.")
    path = tmp_path / "kich_ban.docx"
    document.save(path)

    parts = parse_batch(read_document(path))
    assert [p.marker for p in parts] == ["P1", "P2"]
    assert parts[0].text == "Phần một.\nNội dung phần một."


def test_batch_from_txt_with_bom(tmp_path):
    from core.document_reader import read_document

    path = tmp_path / "kich_ban.txt"
    path.write_text("[P1] A.\n[P2] B.", encoding="utf-8-sig")
    assert [p.marker for p in parse_batch(read_document(path))] == ["P1", "P2"]

