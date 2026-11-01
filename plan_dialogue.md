# KẾ HOẠCH — HỘI THOẠI NHIỀU GIỌNG (`v3.5.0`)

> **Trạng thái:** kế hoạch, **chưa triển khai**.
> **Mốc hiện tại:** `v3.4.0`.
> **Bản đích:** `v3.5.0` — nằm trong đợt đổi UI SaaS, **không phát hành trung gian**.
> **Giao diện:** hội thoại là **một page** trong shell mới, không phải tab/dialog.
> **Tài liệu liên quan:** `plan_ui_saas.md` (shell, palette, router, player chung) · `plan_update.md`.
> **Ngày cập nhật:** 01/11/2026

---

## 1. Mục tiêu

Tạo **một file audio liền mạch** từ kịch bản nhiều nhân vật, mỗi nhân vật một giọng,
ghép xen kẽ đúng thứ tự, có khoảng nghỉ giữa lượt; nghe thử và xuất MP3/WAV.
Toàn bộ nằm trong **`DialoguePage`** của shell SaaS.

| Trong phạm vi | Ngoài phạm vi |
|---|---|
| Kịch bản `Tên: nội dung`, gán giọng từng nhân vật | Xuất `.srt` / `.vtt` (đã bỏ từ 3.2.0) |
| Ghép 1 file, nghe thử, xuất file | Mỗi lượt một file riêng |
| Page riêng trong sidebar, dùng player chung | Dubbing theo video/phụ đề |
| Tự nhớ giọng theo tên nhân vật + tự lưu nháp | Nhập/xuất kịch bản JSON |
| Dùng chung TagBar, Từ điển, waveform/player | Đọc tên nhân vật (“An nói: …”) |
| `infer()` từng câu như luồng hiện tại | `infer_batch` (xem mục 10) |

---

## 2. Quyết định đã chốt

| # | Nội dung | Quyết định |
|---|---|---|
| 1 | Dòng không có `Tên:` | ❌ **Lỗi chặn** — báo đúng số dòng + nút “Sửa dòng này” |
| 2 | Đọc tên nhân vật | ❌ Không có tuỳ chọn |
| 3 | Lưu/mở kịch bản | ❌ Không JSON với người dùng; tự lưu nháp + tự nhớ giọng (ngầm) |
| 4 | Vị trí UI | **Page “Hội thoại”** trong sidebar shell SaaS (xem `plan_ui_saas.md`) |
| 5 | Bố cục page | Trái: editor kịch bản; Phải: card “Nhân vật & giọng” (gán, nghe thử, gán tự động, số lượt) |
| 6 | TagBar | Dùng chung như các page khác (thẻ cảm xúc, thẻ nghỉ, Từ điển, Làm sạch) |
| 7 | Nghỉ giữa lượt | Mặc định **0,5 s**; chọn 0,25 / 0,5 / 0,75 / 1,0 / 1,5 s |
| 8 | Hành động chính | `⚡ Tạo hội thoại` + `💾 Xuất file` ở `PageHeader`; đang chạy đổi `⏹ Dừng` |
| 9 | Bản quyền | Chưa kích hoạt vẫn soạn + nghe thử; **khoá xuất file** (2 lớp) |
| 10 | Player | Dùng **PlayerBar chung** (waveform + seek + transport + tốc độ) |

---

## 3. Bố cục `DialoguePage`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Hội thoại nhiều giọng                             [📄 Dán mẫu] [⚡ Tạo] [💾]  │  PageHeader
│ Mỗi dòng: Tên nhân vật: nội dung. Dòng bắt đầu # là chú thích.               │
├───────────────────────────────────────────────┬──────────────────────────────┤
│ Kịch bản                                      │ Nhân vật & giọng             │
│ ┌───────────────────────────────────────────┐ │ An      [Adam bựa ▾]  🔊  4  │
│ │ An: Xin chào, tôi là An.                  │ │ Bình    [Trúc Ly  ▾]  🔊  3  │
│ │ Bình: Chào An. Hôm nay có gì mới?         │ │ ─────────────────────────    │
│ │ An: [nghỉ 1s] Có ba tin đáng chú ý.       │ │ Nghỉ giữa lượt  [0.5s ▾]     │
│ └───────────────────────────────────────────┘ │ [🔁 Gán tự động]             │
│ ⚠ Dòng 4: thiếu “Tên:”  [Sửa dòng này]        │ 2 nhân vật · 6 lượt · 312 ký tự│
├───────────────────────────────────────────────┴──────────────────────────────┤
│ PlayerBar chung: waveform + ⏮ ▶ ⏭ + −5/+5 + thời lượng + 1.0x ▾              │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Editor dùng `SyncTextbox` (đã có undo, highlight câu).
- Card phải là `Card` + `Table`/danh sách hàng: tên, combobox giọng (giọng đang bật), nút 🔊, số lượt.
- Danh sách lỗi dưới editor: mỗi dòng lỗi có nút nhảy con trỏ.
- “📄 Dán mẫu” chèn kịch bản 2 người dẫn 4–6 lượt.
- Khi tạo: highlight nền theo lượt đang đọc (dùng timeline char offset).

---

## 4. Định dạng kịch bản

```
# Bản tin phát thanh (dòng bắt đầu # là chú thích, bỏ qua)
An: Xin chào, tôi là An.
Bình: Chào An. Hôm nay có gì mới?
An: [nghỉ 1s] Có ba tin đáng chú ý.
Bình: Mời anh đọc tin đầu tiên.
```

| Trường hợp | Hành vi |
|---|---|
| `Tên: nội dung` | Hợp lệ; tên tối đa 40 ký tự |
| Dòng trống | Bỏ qua |
| Dòng `#…` | Chú thích, bỏ qua |
| **Thiếu `Tên:`** | ❌ Lỗi chặn: “Dòng 4: thiếu `Tên:`” + nút **Sửa dòng này** |
| `Tên:` nhưng nội dung rỗng | ❌ Lỗi chặn |
| Tên chứa `[` `]` hoặc > 40 ký tự | ❌ Lỗi chặn |
| Tên trùng (khác hoa/thường) | ⚠️ Cảnh báo, gộp về một nhân vật |
| Thẻ `[cười]`, `[nghỉ 2s]` trong nội dung | Chạy như hiện tại (`core/tags.py`) |

Mỗi lượt lưu `char_start/char_end` của **phần nội dung** (bỏ tiền tố `Tên:`) để highlight đúng.

---

## 5. Không dùng JSON — người dùng chỉ thấy văn bản

| Việc | Cách làm |
|---|---|
| Soạn kịch bản | Chỉ **dán/gõ trực tiếp** vào page |
| Giữ kịch bản khi đóng app | App **tự lưu nháp** `data_dir()/dialogue_draft.txt`; mở lại tự hiện |
| Nhớ giọng từng nhân vật | App **tự lưu ngầm** `data_dir()/dialogue_cast.json` theo **tên nhân vật** |
| Dùng lại ở máy khác | Ctrl+A → Ctrl+C rồi dán sang máy kia |
| “Mở/Lưu .txt” | ❌ Không có ở 3.5.0 |

`dialogue_cast.json` (nội bộ):

```json
{
  "ver": 1,
  "cast": {
    "An":   {"model_id": "vieneu:Adam bựa", "display_name": "Adam bựa (Nam, Bắc)"},
    "Bình": {"model_id": "vieneu:Trúc Ly", "display_name": "Trúc Ly (Nữ, Bắc)"}
  },
  "options": {"gap_sec": 0.5}
}
```

Giọng bị xoá/đổi tên → fallback giọng đầu tiên đang bật + cảnh báo vàng (không chặn).

---

## 6. Kiến trúc & file

### 6.1. File mới

| File | Vai trò | ~KB |
|---|---|---|
| `core/dialogue.py` | Parse kịch bản, nhân vật, lỗi theo dòng, cast, draft | 11 |
| `engine/dialogue_engine.py` | Dựng audio nhiều giọng, timeline, nghỉ, huỷ | 8 |
| `ui/pages/dialogue_page.py` | Page hội thoại: editor + card nhân vật + tiến trình | 16 |
| `ui/components/dialogue_cast_panel.py` | Card “Nhân vật & giọng” (tách khỏi page để giữ < 25 KB) | 10 |
| `tests/test_dialogue.py` | ~25 test | — |
| `packaging/probe_dialogue.py` | Probe model thật (2 giọng) | — |

### 6.2. File sửa

| File | Thay đổi |
|---|---|
| `ui/shell/app_shell.py` | Đăng ký page `dialogue` + route `Ctrl+2` |
| `ui/shell/nav_sidebar.py` | Mục “🎭 Hội thoại” (đã có trong danh sách) |
| `ui/window/convert.py` → `SessionController` | Thêm nhánh render hội thoại dùng chung message protocol |
| `ui/window/export.py` → controller | Xuất theo session của page; lịch sử preview kịch bản |
| `ui/window/tools.py`, `license_ui.py` | Gate bản quyền cho page |
| `engine/vieneu_engine.py` | `set_voice(voice_id)` |
| `core/text_processor.py` | `clean_for_reading()` không gộp dòng có tiền tố `Tên:` |
| `packaging/probe_menu_toolbar.py` … | Probe cũ theo shell mới |
| `version.py`, HDSD, README, `plan_update.md` | 3.5.0 + tài liệu |

### 6.3. Phiên âm thanh

Dùng `AudioSession` của shell (xem `plan_ui_saas.md` mục 5.3). Page hội thoại sở hữu
một phiên; khi rời page, audio/timeline vẫn giữ; PlayerBar ẩn/hiện theo phiên.

---

## 7. Luồng xử lý

```
Kịch bản (dán vào page)
  → core.dialogue.parse_script()        # lượt, nhân vật, lỗi, char offset
  → gán giọng (card phải / gán tự động) # lưu ngầm theo tên
  → engine.dialogue_engine.render()
        for mỗi lượt:
            tts.set_voice(model_id)             # đổi giọng, KHÔNG nạp lại model
            TtsEngine(tts).synthesize_stream(lượt)
            cộng dồn store (RAM hoặc file tạm)
            chèn khoảng lặng giữa lượt (0,25–1,5 s)
        áp tốc độ 1 lần cuối (apply_speed + timeline.scaled)
  → TimelineMap (char offset quy về kịch bản gốc)
  → PlayerBar (nghe thử) | xuất MP3/WAV (exporter.export_source)
```

Chi tiết:

- **Đổi giọng**: `Vieneu.infer(text, voice=name)` nhận `voice` mỗi lần gọi → `set_voice()` không nạp lại model (8–10 s).
- **Timeline**: đánh lại `index` liên tục toàn bài; `char_start = turn.char_start + sentence.char_start`.
- **Bộ nhớ**: `GrowableBuffer` / `TempSession` + `should_use_disk(text, settings)` như luồng chính.
- **Tốc độ**: tổng hợp ở 1.0x rồi time-stretch một lần.
- **Huỷ**: `threading.Event`; dừng sau lượt hiện tại, không để file dở.
- **Message protocol** dùng lại `stream_init / stream_chunk / stream_base / stream_end`.
- **Busy**: `ctx.set_busy(True)` → khoá sidebar (trừ Lịch sử), nút đổi `⏹ Dừng`.

---

## 8. Kiểm thử

### 8.1. `tests/test_dialogue.py` (~25 case)

| Nhóm | Case |
|---|---|
| Parse | 1 lượt; nhiều lượt; `:` trong nội dung; **thiếu tên → lỗi kèm số dòng**; `#`; CRLF; dòng rỗng; tên trùng hoa/thường; tên > 40 ký tự; nội dung rỗng; tên chứa `[` |
| Offset | `char_start/char_end` trỏ đúng nội dung (không gồm `Tên:`) |
| Cast | lưu/đọc theo tên; giọng bị xoá → fallback; thêm nhân vật giữ mapping cũ |
| Draft | tự lưu/khôi phục `dialogue_draft.txt`; file hỏng → rỗng, không crash |
| Engine (FakeTTS) | mỗi lượt gọi đúng `set_voice`; đúng thứ tự; nghỉ giữa lượt; nghỉ cuối = 0; timeline liên tục; `[nghỉ 2s]` trong lượt; huỷ giữa chừng |
| Làm sạch | `clean_for_reading` không gộp 2 dòng `An: …` / `Bình: …` |

### 8.2. `packaging/probe_dialogue.py` (model thật)

1. 2 nhân vật × 2 lượt, 2 giọng khác giới → xuất MP3.
2. File > 0; thời lượng ≥ tổng 4 lượt; timeline 4+ câu; `char_start` khớp kịch bản.
3. So sánh 2 đoạn audio 2 giọng (tương quan < 0,95) để chắc `set_voice` có tác dụng.
4. Dòng thiếu tên → chặn tạo, báo đúng số dòng.
5. Chưa kích hoạt → xuất bị chặn, vẫn nghe thử được.
6. Xuất xong có 1 mục lịch sử.

### 8.3. Hồi quy

`pytest` hiện có + ~25 test mới; `probe_navigation`/`probe_shell` của kế hoạch UI; `check_code_size` (< 25 KB/file).

---

## 9. Vì sao không dùng `infer_batch`

1. Mỗi batch **chỉ một giọng** → phải nhóm theo giọng rồi ghép lại, phức tạp timeline.
2. Trên CPU vẫn chạy tuần tự → **không nhanh hơn**.
3. Mất kiểm soát thẻ `[nghỉ 3s]` và khoảng nghỉ từng câu.

→ Bản 3.5.0 gọi `infer()` từng câu. Chỉ xem lại khi có GPU.

---

## 10. Giai đoạn (nằm trong P4 của kế hoạch UI)

| Bước | Việc | Điều kiện xong | Ước lượng |
|---|---|---|---|
| **D1** | `core/dialogue.py` + test parse/cast/draft | ~15 test pass | 1 ngày |
| **D2** | `set_voice` + `dialogue_engine.py` + test FakeTTS | ~10 test pass | 1 ngày |
| **D3** | `dialogue_page.py` + `dialogue_cast_panel.py` + route sidebar + gate + lịch sử | Page chạy đủ: soạn, gán, tạo, xuất, lỗi dòng | 1,5 ngày |
| **D4** | `probe_dialogue` (model thật) + tinh chỉnh + HDSD/README | Probe pass, tài liệu cập nhật | 0,5–1 ngày |

**Tổng: ~4 ngày** (P0 tách menubar/header của bản kế hoạch cũ đã bị loại — nay nằm trong P0 của `plan_ui_saas.md`).

---

## 11. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| `set_voice` không đổi giọng thật | Trung bình | Probe D4 so sánh 2 đoạn audio; nếu lỗi → nạp lại model theo giọng (chậm hơn) |
| Hội thoại dài → RAM tăng | Trung bình | `TempSession` khi > 20.000 ký tự |
| Highlight lệch | Thấp | Offset tính từ phần nội dung; test riêng |
| Card nhân vật làm page > 25 KB | Trung bình | Tách `dialogue_cast_panel.py`; `check_code_size` chặn build |
| Khách chưa kích hoạt vẫn xuất được | Cao | Gate 2 lớp (mở page + worker) |
| CPU chậm với kịch bản dài (RTF ~0,6) | Trung bình | Tiến trình theo lượt + Dừng; ghi rõ “~1 phút audio ≈ 40 giây máy” |
| Giọng đã xoá nhưng còn trong cast | Thấp | Fallback + cảnh báo, không chặn |
| Chuyển trang khi đang tạo | Cao | `ctx.set_busy` khoá sidebar; `on_hide` dừng worker an toàn |

---

## 12. Định nghĩa hoàn thành

- [ ] Page “Hội thoại” trong sidebar, layout 2 cột theo mục 3
- [ ] Kịch bản: lỗi thiếu tên chặn tạo + nhảy tới dòng lỗi
- [ ] Không có UI JSON; tự lưu nháp + tự nhớ giọng theo tên
- [ ] Hội thoại 2+ giọng: đúng thứ tự, nghỉ giữa lượt, timeline/highlight đúng
- [ ] Xuất MP3/WAV + 1 mục lịch sử; gate bản quyền 2 lớp
- [ ] Dùng PlayerBar chung; chuyển trang không mất audio
- [ ] `pytest` ~25 test mới pass; `probe_dialogue` pass; `check_code_size` OK
- [ ] HDSD/README/`plan_update.md` cập nhật trong bản 3.5.0

---

## 13. Việc chưa làm

- “Mở/Lưu .txt” cho kịch bản (chỉ dán text).
- Xuất `.srt` (đã bỏ từ 3.2.0).
- `infer_batch` (chờ GPU).
- Đọc tên nhân vật (đã bỏ theo yêu cầu).
