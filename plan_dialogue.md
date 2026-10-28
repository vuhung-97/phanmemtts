# KẾ HOẠCH — HỘI THOẠI NHIỀU GIỌNG (`v3.5.0`)

> **Trạng thái:** kế hoạch, **chưa triển khai**.
> **Mốc hiện tại:** `v3.4.0` (đã có từ điển, làm sạch, chuyển đổi hàng loạt, điều khoản).
> **Ngày lập:** 28/10/2026
> **Người chốt quyết định:** chủ phần mềm (xem mục 2).

---

## 1. Mục tiêu

Tạo **một file audio liền mạch** từ kịch bản nhiều nhân vật, mỗi nhân vật một giọng,
ghép xen kẽ đúng thứ tự, có khoảng nghỉ giữa lượt, nghe thử và xuất MP3/WAV.

| Trong phạm vi | Ngoài phạm vi |
|---|---|
| Kịch bản `Tên: nội dung`, gán giọng từng nhân vật | Xuất `.srt` / `.vtt` (mục 2.1 đã bỏ từ 3.2.0) |
| Ghép 1 file, nghe thử, xuất file | Mỗi lượt một file riêng |
| Hiển thị thành **tab trên trang chính**, cạnh tab Văn bản | Dubbing theo video/phụ đề |
| Tự nhớ giọng theo tên nhân vật + tự lưu nháp kịch bản | Nhập/xuất kịch bản bằng JSON |
| Dùng chung waveform/playback/TagBar/Từ điển | Đọc tên nhân vật (“An nói: …”) |
| `infer()` từng câu như luồng hiện tại | `infer_batch` (xem mục 9) |

---

## 2. Quyết định đã chốt

| # | Nội dung | Quyết định |
|---|---|---|
| 1 | Dòng không có `Tên:` | ❌ **Lỗi chặn** — báo đúng số dòng, nút “Sửa dòng này” đưa con trỏ tới; không tự gán “Người dẫn” |
| 2 | Đọc tên nhân vật | ❌ **Không có** tuỳ chọn này |
| 3 | Lưu/mở kịch bản | ❌ **Không dùng JSON**. Chỉ dán/gõ trực tiếp; app tự lưu nháp và tự nhớ giọng (ngầm, người dùng không thấy file) |
| 4 | Giao diện | Tab nằm trên thanh menu; **đổi tab thì đổi toàn bộ 3 hàng header**. Logo chỉ có ở tab Văn bản. Thanh menu + tab + badge bản quyền dùng chung |
| 5 | TagBar | Dùng chung cho cả 2 tab (thẻ cảm xúc, thẻ nghỉ, Từ điển, Làm sạch) |
| 6 | Nghỉ giữa lượt | Mặc định **0,5 s**; chọn 0,25 / 0,5 / 0,75 / 1,0 / 1,5 s |
| 7 | Nút “Tạo” / “Xuất” | Ở panel phải header tab Hội thoại, cùng vị trí/kích thước với tab Văn bản |
| 8 | Bản quyền | Chưa kích hoạt vẫn soạn + nghe thử; **khoá xuất file** (2 lớp: lúc mở tab và trong worker) |

---

## 3. Bố cục giao diện

```
┌ Tệp   Công cụ   Trợ giúp ─────────── [📖 Văn bản][🎭 Hội thoại] ──── 🔑 Còn 23 ngày ┐ 30
├──────────────────────── HEADER CỦA TAB ĐANG MỞ (3 hàng, 146 px) ────────────────────┤
│  TAB VĂN BẢN (giữ nguyên hiện tại)                                                  │
│  [logo] │ 📁 Mở file   tên-file                        │ ⚡ Chuyển đổi             │
│         │ Giọng đọc [Adam ▾] ＋   Tốc độ [1.0x ▾]       │ 💾 Xuất file              │
│         │ 🔊 Test  [câu test …………………]                 │                           │
│         │ dòng trạng thái                                                          │
├──────────────────────────────────────────────────────────────────────────────────────┤
│  TAB HỘI THOẠI (không logo — dùng hết chiều ngang)                                  │
│  📄 Dán mẫu    2 nhân vật · 6 lượt · 312 ký tự          │ ⚡ Tạo hội thoại          │
│  Tốc độ [1.0x ▾]   Nghỉ giữa lượt [0.5s ▾]              │ 💾 Xuất file             │
│  🎭 Giọng nhân vật (2)   🔁 Gán tự động                                           │
│  dòng trạng thái / danh sách dòng lỗi                                               │
├──────────────────────── TagBar dùng chung (34 px) ──────────────────────────────────┤
│ [cười] [thở dài] [hắng giọng] │ ⏸ Nghỉ ▾ │ gợi ý        📖 Từ điển   🧹 Làm sạch  │
├──────────────────────── Khung soạn thảo / Kịch bản (334 px) ────────────────────────┤
├──────────────────────── Waveform timeline (dùng chung) ─────────────────────────────┤
├──────────────────────── Playback bar (dùng chung) ──────────────────────────────────┤
```

- Không tăng chiều cao: menu 30 + header 146 = **176 px** như hiện tại; khung soạn thảo giữ **334 px @980×740**.
- Tab Văn bản **không thay đổi** so với 3.4.0.
- Tab Hội thoại: `⚡ Tạo hội thoại` (đổi nhãn khi đang chạy thành `⏹ Dừng`), `💾 Xuất file`.
- Ở tab Hội thoại, ô **Giọng đọc** và nút **Test** của tab Văn bản không tồn tại (header đã đổi) — giọng chọn theo từng nhân vật.

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
| Thẻ `[cười]`, `[nghỉ 2s]` trong nội dung | Chạy như hiện tại (do `core/tags.py` xử lý) |

Mỗi lượt lưu `char_start/char_end` của **phần nội dung** (bỏ tiền tố `Tên:`) để highlight đúng câu đang đọc.

---

## 5. Không dùng JSON — người dùng chỉ thấy văn bản

| Việc | Cách làm |
|---|---|
| Soạn kịch bản | Chỉ **dán/gõ trực tiếp** vào tab |
| Giữ kịch bản khi đóng app | App **tự lưu nháp** `data_dir()/dialogue_draft.txt`; mở lại app tự hiện lại |
| Nhớ giọng từng nhân vật | App **tự lưu ngầm** `data_dir()/dialogue_cast.json` theo **tên nhân vật**; gõ lại `An:` → tự gán giọng cũ |
| Dùng lại kịch bản ở máy khác | Ctrl+A → Ctrl+C rồi dán sang máy kia (không cần file) |
| Nút “📄 Dán mẫu” | Chèn kịch bản mẫu 2 người dẫn (4–6 lượt) để thấy cách viết |
| “Mở/Lưu .txt” | **Không có ở 3.5.0** (theo yêu cầu “chỉ dán text”); có thể bổ sung sau |

`dialogue_cast.json` (nội bộ) có dạng:

```json
{
  "ver": 1,
  "cast": {
    "An":   {"model_id": "vieneu:Adam bựa", "display_name": "Adam bựa (Nam, Bắc)"},
    "Bình": {"model_id": "vieneu:Trúc Ly", "display_name": "Trúc Ly (Nữ, Bắc)"}
  },
  "options": {"gap_sec": 0.5, "speed": 1.0}
}
```

Giọng đã bị xoá/đổi tên → tự fallback giọng đầu tiên đang bật + cảnh báo vàng (không chặn).

---

## 6. Kiến trúc & file

### 6.1. File mới

| File | Vai trò | ~KB |
|---|---|---|
| `core/dialogue.py` | Parse kịch bản, danh sách nhân vật, lỗi theo dòng, cast, draft | 11 |
| `engine/dialogue_engine.py` | Dựng audio nhiều giọng, timeline, nghỉ, huỷ | 8 |
| `ui/components/menubar.py` | Thanh menu + 2 nút tab + badge + phím tắt | 9 |
| `ui/components/dialogue_header.py` | Header tab Hội thoại (3 hàng) | 12 |
| `ui/components/dialogue_cast_dialog.py` | Bảng gán giọng + nghe thử từng giọng | 14 |
| `tests/test_dialogue.py` | ~25 test | — |
| `packaging/probe_tabs.py` | Probe chuyển tab + state | — |
| `packaging/probe_dialogue.py` | Probe model thật (2 giọng) | — |

### 6.2. File sửa

| File | Thay đổi |
|---|---|
| `ui/components/topbar.py` | Bỏ phần menu bar (chuyển sang `menubar.py`); chỉ còn header tab Văn bản; API giữ nguyên |
| `ui/main_window.py` | Grid lại 6 hàng; `SessionState` cho 2 tab; `set_mode()`; snapshot/restore |
| `ui/window/convert.py` | `_start_convert()` rẽ nhánh tab; `_start_dialogue_convert()` dùng chung message protocol |
| `ui/window/export.py` | Xuất theo tab; lịch sử ghi preview kịch bản khi ở tab hội thoại |
| `ui/window/tools.py` | Menu “Hội thoại nhiều giọng…” = chuyển tab; gate bản quyền |
| `engine/vieneu_engine.py` | Thêm `set_voice(voice_id)` (chỉ gán biến, không nạp lại model) |
| `core/text_processor.py` | `clean_for_reading()` **không gộp** dòng có tiền tố `Tên:` |
| `packaging/probe_menu_toolbar.py` | Cập nhật kỳ vọng (menubar tách riêng, có tab) |
| `version.py` | 3.5.0 |
| `docs/gen_hdsd_v3.py`, `README.md`, `plan_update.md` | Tài liệu + nhật ký |

### 6.3. Trạng thái mỗi tab (`SessionState`)

```
editor, synth_text, base_store, play_store, base_timeline, timeline,
base_spans, applied_speed, speed_dirty, disk_mode, temp_session,
store_seq, current_sentence, stream_total_sentences,
stream_has_started_playing, last_waveform_draw
```

- `self._sessions = {"text": SessionState(), "dialogue": SessionState()}`
- Chuyển tab: lưu state tab cũ → `player.stop()` → nạp state tab mới → vẽ lại waveform/timeline/highlight.
- Giữ nguyên tên thuộc tính cũ, chỉ thay bằng proxy tới `self._session` để hạn chế sửa mixin.

---

## 7. Luồng xử lý

```
Kịch bản (dán vào tab)
  → core.dialogue.parse_script()        # lượt, nhân vật, lỗi, char offset
  → gán giọng (chip/dialog/tự động)     # lưu ngầm theo tên nhân vật
  → engine.dialogue_engine.render()
        for mỗi lượt:
            tts.set_voice(model_id)             # đổi giọng, KHÔNG nạp lại model
            TtsEngine(tts).synthesize_stream(lượt)   # giữ chuẩn câu/pad/fade/thẻ
            cộng dồn vào store (RAM hoặc file tạm)
            chèn khoảng lặng giữa lượt (0,25–1,5 s)
        áp tốc độ 1 lần cuối (apply_speed + timeline.scaled)
  → TimelineMap (char offset quy về kịch bản gốc)
  → nghe thử (player chung) | xuất MP3/WAV (exporter.export_source)
```

Chi tiết:

- **Đổi giọng**: `Vieneu.infer(text, voice=name)` nhận `voice` mỗi lần gọi → `set_voice()` không gây nạp lại model (8–10 giây).
- **Timeline**: đánh lại `index` liên tục toàn bài; `char_start = turn.char_start + sentence.char_start`.
- **Bộ nhớ**: `GrowableBuffer` hoặc `TempSession` + `should_use_disk(text, settings)` như luồng chính.
- **Tốc độ**: tổng hợp ở 1.0x rồi time-stretch một lần (cao độ không méo, khoảng nghỉ co giãn đồng bộ).
- **Huỷ**: `threading.Event`; dừng sau lượt hiện tại, không để file dở.
- **Message protocol**: dùng lại `stream_init / stream_chunk / stream_base / stream_end` để phần xử lý UI/player ít phải sửa.

---

## 8. Kiểm thử

### 8.1. `tests/test_dialogue.py` (~25 case, không cần model)

| Nhóm | Case |
|---|---|
| Parse | 1 lượt; nhiều lượt; `:` trong nội dung; **thiếu tên → lỗi kèm số dòng**; `#`; CRLF; dòng rỗng; tên trùng hoa/thường; tên > 40 ký tự; nội dung rỗng; tên chứa `[` |
| Offset | `char_start/char_end` trỏ đúng nội dung (không gồm `Tên:`) |
| Cast | lưu/đọc theo tên; giọng bị xoá → fallback; thêm nhân vật giữ mapping cũ |
| Draft | tự lưu/khôi phục `dialogue_draft.txt`; file hỏng → rỗng, không crash |
| Engine (FakeTTS) | mỗi lượt gọi đúng `set_voice`; đúng thứ tự; nghỉ giữa lượt; nghỉ cuối = 0; timeline liên tục; `[nghỉ 2s]` trong lượt; huỷ giữa chừng |
| Làm sạch | `clean_for_reading` không gộp 2 dòng `An: …` / `Bình: …` |

### 8.2. `packaging/probe_tabs.py`

1. Có đúng 2 tab; bấm qua lại, header đổi nội dung, chiều cao không đổi.
2. Chuyển đổi ở tab Văn bản → sang Hội thoại → quay lại: audio/timeline/waveform còn nguyên, xuất đúng file.
3. Tạo hội thoại → về tab Văn bản: audio tab văn bản còn nguyên.
4. Đang chạy: tab bị khoá, nút ⚡ đổi thành ⏹; menu chuyển tab cũng bị chặn.
5. Kích thước @980/1100/1200/1440: header 176 px, textbox ≥ 300 px.
6. Menu Công cụ → Hội thoại chuyển đúng tab (không mở dialog).

### 8.3. `packaging/probe_dialogue.py` (model thật)

1. 2 nhân vật × 2 lượt, 2 giọng khác giới → xuất MP3.
2. Kiểm tra: file > 0; thời lượng ≥ tổng 4 lượt; timeline 4+ câu; `char_start` khớp kịch bản.
3. So sánh 2 đoạn audio 2 giọng (tương quan < 0,95) để chắc `set_voice` có tác dụng.
4. Dòng thiếu tên → chặn tạo, báo đúng số dòng.
5. Chưa kích hoạt → xuất bị chặn, vẫn nghe thử được.
6. Xuất xong có 1 mục lịch sử.

### 8.4. Hồi quy

`pytest` 210 + ~25 mới; 7 probe cũ; `check_code_size` (mỗi file < 25 KB code object).

---

## 9. Vì sao không dùng `infer_batch`

SDK có `infer_batch(texts, voice=...)` nhưng:

1. Mỗi batch **chỉ một giọng** → phải nhóm theo giọng rồi ghép lại, làm phức tạp timeline.
2. Trên CPU vẫn chạy tuần tự → **không nhanh hơn**.
3. Mất kiểm soát thẻ `[nghỉ 3s]` và khoảng nghỉ từng câu (những thứ app đang tự xử lý).

→ Bản 3.5.0 gọi `infer()` từng câu. Chỉ xem lại nếu sau này có GPU.

---

## 10. Giai đoạn triển khai

| Phase | Việc | Điều kiện xong | Ước lượng |
|---|---|---|---|
| **P0** | Tách `menubar.py`, stack header, `SessionState`, `set_mode()` | Tab Văn bản chạy y như 3.4.0; header 176 px; textbox 334 px; chuyển tab 2 chiều giữ audio | 1,5 ngày |
| **P1** | `core/dialogue.py` + test parse/cast/draft | ~15 test pass | 1 ngày |
| **P2** | `set_voice` + `dialogue_engine.py` + test FakeTTS | ~10 test pass | 1 ngày |
| **P3** | `dialogue_header` + `dialogue_cast_dialog` + convert/export theo tab | Tạo + xuất + lịch sử + gate hoạt động | 1,5 ngày |
| **P4** | `probe_tabs` + `probe_dialogue` + HDSD/README + build 3.5.0 | Toàn bộ probe pass + gói update 3.4.0 → 3.5.0 | 1 ngày |

**Tổng: ~6 ngày.**

---

## 11. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Snapshot/restore sót trường → xuất nhầm audio tab kia | Cao | `SessionState` dataclass; probe 2 chiều; so `_timeline` sau khi chuyển tab |
| RAM tăng vì giữ audio 2 tab | Trung bình | Text dài đã dùng đĩa; giải phóng phiên không hoạt động khi > 5 phút audio |
| Chuyển tab khi đang chạy làm hỏng worker | Cao | Khoá tab + menu khi `_busy`; chỉ đổi tab khi rảnh |
| `set_voice` không đổi giọng thật | Trung bình | Probe P2 so sánh 2 đoạn audio; nếu lỗi → nạp lại model theo giọng (chậm hơn) |
| Header hội thoại vượt chiều cao / lệch layout | Trung bình | Giữ đúng 3 hàng 56/56/34; `probe_tabs` đo 4 bề rộng |
| TagBar bó hẹp @980 | Trung bình | Giữ nguyên TagBar hiện tại; chỉ thêm 2 nút tab trên menu row |
| Dialog bảng giọng > 32 KB PyArmor | Trung bình | File riêng (~14 KB); `check_code_size` chặn build |
| Khách chưa kích hoạt vẫn xuất được | Cao | Gate 2 lớp (mở tab + worker), giống luồng Xuất file |
| CPU chậm với kịch bản dài (RTF ~0,6) | Trung bình | Tiến trình theo lượt + nút Dừng; ghi rõ “~1 phút audio ≈ 40 giây máy” |
| Giọng đã xoá nhưng còn trong cast | Thấp | Fallback + cảnh báo, không chặn |

---

## 12. Định nghĩa hoàn thành (DoD)

- [ ] 2 tab hoạt động; tab Văn bản không hồi quy (header 176 px, textbox 334 px @980×740)
- [ ] Header đổi hoàn toàn theo tab; logo chỉ ở tab Văn bản
- [ ] Kịch bản: lỗi thiếu tên chặn tạo + nhảy tới dòng lỗi
- [ ] Không có UI JSON; tự lưu nháp + tự nhớ giọng theo tên
- [ ] Hội thoại 2+ giọng: đúng thứ tự, nghỉ giữa lượt, timeline/highlight đúng
- [ ] Xuất MP3/WAV + ghi 1 mục lịch sử; gate bản quyền 2 lớp
- [ ] `pytest` ~235 pass; 9 probe pass; `check_code_size` OK
- [ ] Build `v3.5.0` + `update_3.5.0.zip`; HDSD/README/plan_update cập nhật

---

## 13. Việc chưa làm (ghi chú)

- “Mở/Lưu .txt” cho kịch bản: chưa có (theo yêu cầu chỉ dán text). Có thể bổ sung ở bản sau.
- Xuất `.srt`: đã bỏ từ 3.2.0.
- `infer_batch`: chỉ xem lại khi có GPU.
- Đa nền tảng: đã bỏ khỏi scope từ 3.4.0.
