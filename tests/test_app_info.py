"""Tên app lấy từ app_config.json, có fallback an toàn."""

from __future__ import annotations

import version
from core.app_info import load_app_name


def test_doc_ten_tu_json(tmp_path):
    path = tmp_path / "app_config.json"
    path.write_text('{"app_name": "  Phần mềm   của tôi  "}',
                    encoding="utf-8")
    assert load_app_name(path) == "Phần mềm của tôi"


def test_bo_qua_bom_utf8(tmp_path):
    path = tmp_path / "app_config.json"
    path.write_text('{"app_name": "Bản có BOM"}', encoding="utf-8-sig")
    assert load_app_name(path) == "Bản có BOM"


def test_thieu_file_dung_mac_dinh(tmp_path):
    assert load_app_name(tmp_path / "khong-co.json") == version.__app_name__


def test_json_loi_dung_mac_dinh(tmp_path):
    path = tmp_path / "app_config.json"
    path.write_text("{khong phai json", encoding="utf-8")
    assert load_app_name(path) == version.__app_name__


def test_gia_tri_rong_hoac_sai_kieu(tmp_path):
    path = tmp_path / "app_config.json"
    for content in ('{"app_name": "   "}', '{"app_name": 123}', "[]"):
        path.write_text(content, encoding="utf-8")
        assert load_app_name(path) == version.__app_name__


def test_gioi_han_do_dai(tmp_path):
    path = tmp_path / "app_config.json"
    name = "A" * 300
    path.write_text('{"app_name": "%s"}' % name, encoding="utf-8")
    assert len(load_app_name(path)) == 120
