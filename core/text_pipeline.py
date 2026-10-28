"""Chuỗi xử lý văn bản trước khi đưa một mảnh câu vào model TTS.

Thứ tự (quan trọng — đổi thứ tự sẽ làm sai phát âm):

1. **Chuẩn hoá dấu nháy / gạch nối** về ASCII để model không nhại ký tự lạ.
2. **Từ điển phát âm** (``core.dictionary``): ``KTX`` -> ``ký túc xá``.
   Làm trước bước 3 để chữ thay thế không bị cắt nhỏ.
3. **Chuẩn hoá số** (``core.text_normalizer``): ``2024`` -> ``hai nghìn…``.
   Normalizer tự bỏ qua nội dung trong ``[...]``.
4. **Bổ sung dấu kết câu** nếu thiếu (model đọc tự nhiên hơn).

Dùng chung cho mọi luồng: chuyển đổi, nghe thử, batch, hội thoại — nhờ vậy
từ điển có tác dụng ở tất cả các luồng, không chỉ luồng chính.
"""

from __future__ import annotations

from core.dictionary import apply_dictionary
from core.text_normalizer import normalize_numbers_vi

TERMINAL_CHARS = ".?!…"

SPECIAL_QUOTES: dict[str, str] = {
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "–": "-", "—": "-", "…": "...",
}


def normalize_quotes(text: str) -> str:
    """Đổi dấu nháy cong / gạch dài về ASCII."""
    for src, dst in SPECIAL_QUOTES.items():
        if src in text:
            text = text.replace(src, dst)
    return text


def prepare_for_tts(text: str, *, use_dictionary: bool = True) -> str:
    """Chuẩn bị một mảnh câu để đưa vào model (từ điển -> số -> dấu câu)."""
    text = normalize_quotes(text.strip())
    if use_dictionary:
        text = apply_dictionary(text)
    text = normalize_numbers_vi(text.strip())
    if not text:
        return text
    if text[-1] not in TERMINAL_CHARS:
        text += "."
    return text
