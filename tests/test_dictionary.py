"""Kiểm thử từ điển phát âm và pipeline văn bản."""

from __future__ import annotations

import json

import pytest

from core import dictionary
from core.text_pipeline import normalize_quotes, prepare_for_tts


def doc(*entries: dict, enabled: bool = True) -> dict:
    return {"ver": 1, "enabled": enabled, "entries": list(entries)}


def entry(src: str, dst: str, **kw) -> dict:
    return {"from": src, "to": dst, **kw}


# ── Áp dụng ──

def test_replaces_whole_word_only():
    d = doc(entry("KTX", "ký túc xá"))
    assert dictionary.apply_dictionary("Ở KTX có gì?", d) == "Ở ký túc xá có gì?"
    assert dictionary.apply_dictionary("KTXL không đổi", d) == "KTXL không đổi"


def test_whole_word_false_replaces_inside():
    d = doc(entry("KTX", "ký túc xá", whole_word=False))
    assert dictionary.apply_dictionary("KTXL", d) == "ký túc xáL"


def test_case_insensitive_by_default():
    d = doc(entry("TP.HCM", "thành phố Hồ Chí Minh"))
    assert (dictionary.apply_dictionary("Về tp.hcm nhé", d)
            == "Về thành phố Hồ Chí Minh nhé")


def test_case_sensitive_option():
    d = doc(entry("Minh", "Mình", case_sensitive=True))
    assert dictionary.apply_dictionary("Minh và minh", d) == "Mình và minh"


def test_longest_phrase_wins():
    d = doc(entry("TP", "thành phố"), entry("TP.HCM", "thành phố Hồ Chí Minh"))
    assert (dictionary.apply_dictionary("TP.HCM và TP Hà Nội", d)
            == "thành phố Hồ Chí Minh và thành phố Hà Nội")


def test_does_not_touch_tags():
    d = doc(entry("nghỉ", "NGHỈ"), entry("cười", "CƯỜI"))
    text = "Chờ [nghỉ 2s] rồi [cười] nhé"
    assert dictionary.apply_dictionary(text, d) == text


def test_disabled_dictionary_is_noop():
    d = doc(entry("KTX", "ký túc xá"), enabled=False)
    assert dictionary.apply_dictionary("KTX", d) == "KTX"


def test_replacement_with_backslashes_is_literal():
    d = doc(entry("a", r"\1"))
    assert dictionary.apply_dictionary("a a", d) == r"\1 \1"


def test_duplicate_source_keeps_first():
    d = doc(entry("KTX", "một"), entry("KTX", "hai"))
    assert dictionary.apply_dictionary("KTX", d) == "một"


# ── Kiểm tra / chuẩn hoá ──

@pytest.mark.parametrize("src,dst", [
    ("", "x"), ("  ", "x"), ("x", ""), ("x", "  "), ("[P1]", "một"),
    ("a" * 61, "x"), ("x", "y" * 201),
])
def test_validate_entry_rejects_invalid(src, dst):
    with pytest.raises(ValueError):
        dictionary.validate_entry(src, dst)


def test_validate_entry_strips_spaces():
    assert dictionary.validate_entry("  KTX ", " ký túc xá ") == ("KTX", "ký túc xá")


def test_normalize_doc_drops_broken_entries():
    raw = {
        "ver": 99,
        "enabled": False,
        "entries": [
            {"from": "KTX", "to": "ký túc xá"},
            {"from": "", "to": "x"},
            "không phải dict",
            {"from": "A", "to": "B", "whole_word": False},
        ],
    }
    out = dictionary.normalize_doc(raw)
    assert out["enabled"] is False
    assert [e["from"] for e in out["entries"]] == ["KTX", "A"]
    assert out["entries"][1]["whole_word"] is False


def test_normalize_doc_handles_garbage():
    assert dictionary.normalize_doc("abc")["entries"] == []
    assert dictionary.normalize_doc(None)["entries"] == []


# ── Đọc / ghi ──

def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "dict.json"
    dictionary.save(doc(entry("KTX", "ký túc xá")), path)
    out = dictionary.load(path)
    assert out["enabled"] is True
    assert out["entries"][0]["from"] == "KTX"
    assert dictionary.apply_dictionary("KTX", out) == "ký túc xá"


def test_load_missing_or_corrupt_returns_empty(tmp_path):
    missing = tmp_path / "missing.json"
    assert dictionary.load(missing)["entries"] == []
    bad = tmp_path / "bad.json"
    bad.write_text("{ không phải json", encoding="utf-8")
    assert dictionary.load(bad)["entries"] == []


def test_export_import_and_merge(tmp_path):
    src = tmp_path / "a.json"
    dictionary.save(doc(entry("KTX", "ký túc xá")), src)
    exported = tmp_path / "export.json"
    dictionary.export_to(src, exported)
    assert json.loads(exported.read_text(encoding="utf-8"))["entries"]

    incoming = tmp_path / "incoming.json"
    dictionary.save(doc(entry("UBND", "uỷ ban nhân dân")), incoming)
    merged = dictionary.import_from(incoming, merge=True)
    # merge=True đọc từ điển thật -> chỉ cần có mục mới, không mất dữ liệu cũ
    assert any(e["from"] == "UBND" for e in merged["entries"])


# ── Pipeline ──

def test_normalize_quotes():
    assert normalize_quotes("“Xin chào” — nhé…") == '"Xin chào" - nhé...'


def test_prepare_for_tts_adds_terminal_and_numbers():
    assert prepare_for_tts("Năm 2024") == "Năm hai nghìn không trăm hai mươi bốn."


def test_prepare_for_tts_keeps_existing_terminal():
    assert prepare_for_tts("Xong rồi!") == "Xong rồi!"


def test_prepare_for_tts_empty():
    assert prepare_for_tts("   ") == ""


def test_prepare_for_tts_uses_dictionary(monkeypatch, tmp_path):
    path = tmp_path / "dict.json"
    dictionary.save(doc(entry("KTX", "ký túc xá")), path)
    monkeypatch.setattr(dictionary, "dictionary_path", lambda: path)
    dictionary.invalidate_cache()
    assert prepare_for_tts("Về KTX") == "Về ký túc xá."
    dictionary.invalidate_cache()


def test_prepare_for_tts_can_skip_dictionary(monkeypatch, tmp_path):
    path = tmp_path / "dict.json"
    dictionary.save(doc(entry("KTX", "ký túc xá")), path)
    monkeypatch.setattr(dictionary, "dictionary_path", lambda: path)
    dictionary.invalidate_cache()
    assert prepare_for_tts("Về KTX", use_dictionary=False) == "Về KTX."
    dictionary.invalidate_cache()


def test_number_inside_tag_not_normalized():
    assert prepare_for_tts("Chờ [nghỉ 2s] nhé") == "Chờ [nghỉ 2s] nhé."
