# KẾ HOẠCH CẬP NHẬT — v3.1 → v3.3

> **Trạng thái:** CHỜ CHỐT — chưa triển khai. File này chỉ lưu kế hoạch.
> **Cập nhật 21/10/2026:** Đợt 1 (P0) **đã triển khai xong** — xem mục 10.
> **Người lập:** phiên làm việc nghiên cứu repo `Cuongyd196/cit-voice-studio` + đối chiếu app hiện tại.
> **Mốc code hiện tại:** commit `47873cb` (v3.0.0) — đã push lên `origin/main`.
> **Ngày lập:** 21/10/2026

---

## 0. Bối cảnh

### 0.1 Đối thủ tham chiếu — CIT Voice Studio

| | |
|---|---|
| Repo | `Cuongyd196/cit-voice-studio` — 116★, 46 fork, 35 commit, Apache-2.0 |
| Bản | v1.0.3 (Win `.exe` 363MB · Linux `.deb` 463MB · macOS arm64/x86_64 `.dmg`) |
| **Mã nguồn** | **KHÔNG công khai** — chỉ phát hành bộ cài → so sánh ở mức black-box |
| Kiến trúc | FastAPI/uvicorn + **UI web** (`127.0.0.1:8001`); Windows dùng WebView2, Linux mở trình duyệt, macOS cửa sổ riêng |
| Engine | **VieNeu-TTS v3 Turbo 48 kHz** (giống hệt app mình) + Supertonic 3 (31 ngôn ngữ) |

**Kết luận quan trọng:** cùng engine, cùng 25 giọng preset → chất lượng giọng nói gần như tương đương.
Khác biệt nằm 100% ở **lớp ứng dụng**.

### 0.2 Bảng so sánh tính năng

| Tính năng | CIT | App mình (v3.0.0) |
|---|---|---|
| Engine / chất lượng | VieNeu v3 Turbo 48kHz | VieNeu v3 Turbo 48kHz ✅ |
| 25 giọng preset | ✅ | ✅ (hardcode `PRESET_VOICES`) |
| Nhân bản giọng | Chỉ từ **micro** + câu đồng ý (~8s) | Từ **file mẫu** wav/mp3 (khử nhiễu) — linh hoạt hơn |
| Chia sẻ giọng sang máy khác | ❌ (cấm clone từ file có sẵn) | ✅ file giọng di động `.json` |
| Thẻ cảm xúc `[cười] [thở dài] [hắng giọng]` | ✅ có UI | ⚠️ VieNeu hỗ trợ sẵn, app truyền text thẳng → chạy được nhưng **không có UI** |
| Thẻ nghỉ `[nghỉ 2s]` | ✅ | ❌ |
| Từ điển phát âm (KTX→ký túc xá) | ✅ | ❌ |
| Tốc độ đọc | 0.75x–1.50x cố định | ✅ **0.5x–2.0x, đổi sống, time-stretch giữ cao độ + bù RMS** |
| Đọc file | PDF, DOCX, TXT | DOCX, TXT |
| Phụ đề .srt | ✅ sinh .srt khớp câu | ❌ (đã có `TimelineMap` → dễ làm) |
| Dubbing theo phụ đề | ✅ (đọc đúng mốc, tự chỉnh .srt) | ❌ |
| Batch `[P1][P2]` → nhiều file + zip | ✅ | ❌ |
| Hội thoại / podcast nhiều giọng | ✅ | ❌ (VieNeu SDK có `infer_batch`) |
| Lịch sử bền vững | ✅ | ❌ chỉ `_export_history` trong RAM (10 phần tử) |
| **Ghép nhạc nền + intro/outro + crossfade** | ❌ | ✅ **có** (`ui/components/merge_dialog.py` + `audio/mixer.py`) |
| Waveform + karaoke highlight + seek câu | ⚠️ chỉ nghe thử | ✅ **rất mạnh** |
| API cho app/AI agent khác | ✅ `/api/tts/generate`, `/docs`, `openapi.json` | ❌ (loại khỏi scope) |
| Truy cập LAN + API key | ✅ | ❌ (loại khỏi scope) |
| Ngôn ngữ nước ngoài | ✅ Supertonic 3 | ❌ |
| GPU NVIDIA | ✅ nút "Cài hỗ trợ GPU" | ❌ |
| Quản lý model | ✅ Turbo INT8/GPU/Nano/FP32, làm mờ model không chạy được | ❌ chỉ hardcode fp32 |
| Đa nền tảng | Win + Linux + macOS | ❌ Windows only |
| Pháp lý | ✅ DIEU-KHOAN/PRIVACY + bắt buộc đồng ý khi clone | ❌ |
| Bản 1.0.1+ | Ghi audio dần ra đĩa → không giới hạn độ dài (~84k ký tự, ~1GB RAM) | ⚠️ giữ toàn bộ trong RAM |

### 0.3 Lợi thế cần giữ (CIT không có)

1. **Ghép nhạc**: nhạc nền loop + cắt đoạn + volume + intro/outro + crossfade, có preview và timeline.
2. **Chất lượng phát lại**: time-stretch (librosa) giữ cao độ + bù RMS + fade cosine 2 mép + pause-pad chuẩn VieNeu.
3. **Trải nghiệm nghe**: waveform timeline, highlight câu (karaoke), seek, prev/next câu, đổi tốc độ không cần chạy lại model.
4. **Mã nguồn mở + kiến trúc sạch** (`core/engine/audio/ui` tách lớp, `ModelManager` đa engine).
5. **File giọng di động** — chuyển giọng từ máy khỏe sang máy yếu chỉ bằng 1 file JSON.

### 0.4 Lỗi kỹ thuật đã phát hiện (phải xử lý ở P0)

| # | Vấn đề | Vị trí | Mức |
|---|---|---|---|
| 1 | `np.concatenate` trong vòng lặp stream → **O(n²)**, audio bị copy 3 lần | `ui/main_window.py:537`, `audio/player.py:93` | 🔴 |
| 2 | `num_threads` **không** được truyền xuống SDK (dead code) | `engine/vieneu_engine.py:146` | 🟠 |
| 3 | `precision` cứng `fp32` → RTF ~0.55–0.62, load ~19s (CIT ship INT8: RTF ~0.35, load ~14s) | `engine/vieneu_engine.py:146` | 🟠 |
| 4 | `infer(..., speed=speed)` — SDK v3turbo **không có** param `speed` (bị `**kwargs` nuốt) | `engine/vieneu_engine.py:155` | 🟡 |
| 5 | `librosa` không khai báo trong `requirements.txt` (chỉ nhờ transitive dep) → máy mới thiếu → time-stretch fail **im lặng** | `requirements.txt` | 🟡 |
| 6 | `core/document_reader.py` bị bỏ qua, `main_window._open_file` parse lại | `ui/main_window.py:224` | 🟡 |
| 7 | Normalizer số phá thẻ tùy chỉnh (`[nghỉ 2s]` → `[nghỉ hais]`) | `core/text_normalizer.py` | 🟡 |
| 8 | Chưa có DIEU-KHOAN/PRIVACY + bắt buộc đồng ý khi clone (rủi ro pháp lý) | — | 🟠 |

---

## 1. SCOPE ĐÃ CHỐT

| | Bao gồm | Loại bỏ |
|---|---|---|
| **P0** | O(n²)/RAM, threads+INT8+GPU, dọn code+deps+tests | — |
| **P1** | Xuất .srt · Lịch sử · Từ điển · Thẻ cảm xúc/nghỉ · Làm sạch · Đọc .srt/.vtt + lồng tiếng theo phụ đề · Batch · Model Manager UI | ❌ **Đọc PDF** |
| **P2** | Hội thoại/podcast nhiều giọng · Đa nền tảng (Linux/macOS) · Điều khoản + Privacy | ❌ API server · ❌ LAN/API key |

---

## 2. ĐỢT 1 — P0 → `v3.1.0` (2–3 ngày)

### 2.1 Bộ nhớ & O(n²) 🔴

**File mới `audio/buffer.py`** — `GrowableBuffer` (numpy pre-allocated, capacity ×1.5):

```
append(chunk)   # copy chunk vào, O(len(chunk))
view()          # zero-copy -> self._buf[:self._size]
total_samples, duration
```

Áp dụng:

- `audio/player.py:83` `append_audio` → `GrowableBuffer` (thay `np.concatenate`).
- `ui/main_window.py:537` `stream_chunk` → `GrowableBuffer` (thay `np.concatenate`).
- `ui/main_window.py` `_base_waveform` / `_waveform` → **cùng một buffer** khi speed=1.0; bản speed khác chỉ dựng khi user đổi tốc độ → bỏ 1/3 RAM.
- `waveform_timeline.set_audio()` → nhận `.view()` (zero-copy) + throttle vẽ lại mỗi ~500ms thay vì mỗi câu.

**File mới `audio/temp_store.py`** (bài dài):

- Ghi audio tổng hợp ra `%LOCALAPPDATA%/PhanMemTTS/tmp/<session>/audio.pcm` (PCM16).
- Player đọc bằng `np.memmap`; export stream từ file.
- Bật tự động khi text > 20.000 ký tự (setting `audio_storage: auto|memory|disk`).

**Đạt:** ~84.000 ký tự (~2h audio) chạy với **≤ 1.5 GB RAM**, CPU không tụt dần theo thời gian.

### 2.2 `threads` + `precision` INT8 + GPU 🔴

- `engine/vieneu_engine.py`: `Vieneu(precision=precision, threads=threads)`; bỏ `num_threads` (dead code).
- `engine/model_manager.py`: `load_tts(info, threads=...)` → truyền xuống.
- `ui/config.py`: thêm `app_settings.json` → `{precision, threads, storage, model_preset}`.
- **UI Cài đặt** (dialog mới `ui/components/settings_dialog.py`):
  - Precision: `fp32` / `int8` (mặc định `fp32`; gợi ý INT8 nếu CPU có VNNI)
  - Threads: `0 (auto)` / 2 / 4 / 6 / 8
  - Nút **"Tải model INT8"** → `snapshot_download(allow_patterns=["onnx_int8/*"])` (~1/4 dung lượng)
  - Nút **"Cài hỗ trợ GPU"** → tải `torch` CUDA → `Vieneu(device="cuda")` (RTF 0.55 → 0.02)
- Kiểm tra CPU VNNI: `onnxruntime.get_device_info()` / `platform.processor()` → cảnh báo nếu chọn INT8 mà CPU không hỗ trợ.

**Đạt:** INT8 load ~14s, RTF ~0.35; `threads` có tác dụng thật; GPU bật được qua 1 nút.

### 2.3 Dọn code + dependency + tests 🟠

- `requirements.txt`: thêm `librosa`, `pytest` (dev).
- `engine/vieneu_engine.py:155`: bỏ `speed=speed` khỏi `infer()` (SDK v3turbo không có param này) — speed chỉ do `librosa` xử lý.
- `ui/main_window.py:224` → dùng `core.document_reader.read_document` (bỏ parse trùng).
- `engine/model_manager.py:32` → bỏ nhánh Kokoro/ONNX legacy đã chết.
- **Thêm `tests/`**: `test_text_normalizer.py`, `test_text_processor.py`, `test_timeline.py`, `test_buffer.py`.

### 2.4 Build

- `build_v3.bat`: thêm bước copy `DIEU-KHOAN.md`/`PRIVACY.md` (giai đoạn P2) — chuẩn bị chỗ.
- `packaging/probe_entry.py` + `app_v3_probe.spec`: giữ nguyên, dùng smoke-test TTS trong môi trường frozen sau mỗi đợt.

---

## 3. ĐỢT 2 — P1 → `v3.2.0` (6–8 ngày)

| # | Hạng mục | Chi tiết kỹ thuật |
|---|---|---|
| 2.1 | **Xuất phụ đề .srt** | `audio/subtitles.py::write_srt(timeline, path)` — có sẵn `TimelineMap.sentences` (`start_sec`/`end_sec`). Hộp thoại "Xuất" thêm tuỳ chọn `.srt` + tick "kèm phụ đề" |
| 2.2 | **Lịch sử bền vững** | `core/history.py` + `%LOCALAPPDATA%/PhanMemTTS/history/index.json`; mỗi mục {id, thời gian, giọng, speed, duration, text preview, file wav/mp3/srt}. Tab **Lịch sử**: nghe lại, mở thư mục, xóa, tổng dung lượng, cảnh báo đĩa |
| 2.3 | **Từ điển phát âm** | `core/dictionary.py` + `pronunciation-dict.json`; thay thế theo `\b` **trước** normalizer số; dialog quản lý (thêm/xóa/import-export) + nút trên thanh soạn thảo |
| 2.4 | **Thẻ cảm xúc + thẻ nghỉ** | `core/tags.py`: `[nghỉ 2s]` → tách đoạn, chèn silence **đúng thời lượng** trong `tts_engine` (không phụ thuộc SDK); `[cười]/[thở dài]/[hắng giọng]` → pass-through cho VieNeu. **Bắt buộc:** `core/text_normalizer.py` bỏ qua nội dung trong `[...]`. Thanh chèn nhanh trên khung soạn thảo |
| 2.5 | **Nút "Làm sạch"** | Bỏ dòng trống thừa, gộp xuống dòng giữa câu, **giữ nguyên công thức** `1 + 1` |
| 2.6 | **Đọc .srt/.vtt + Lồng tiếng theo phụ đề** | Parser SRT/VTT tự viết (không dep). Thuật toán: mỗi cue → tổng hợp → `d`; slot = `end - start`; nếu `d > slot` → `apply_speed(min(1.5, d/slot))`; nếu vẫn vượt → **lấn câu sau** (không cắt chữ) và **ghi file .srt đã chỉnh mốc**. UI: danh sách câu + mốc thời gian, nút "Lồng tiếng" |
| 2.7 | **Batch theo marker** | `[P1]`/`[P2]` đầu dòng → mỗi marker 1 file; nhập trực tiếp hoặc file .txt; xuất từng file hoặc 1 **.zip** |
| 2.8 | **Model Manager UI** | Chọn: Turbo INT8 / Turbo fp32 / Turbo GPU NVIDIA / v3 Nano (24 kHz). Model không chạy được → **làm mờ + tooltip lý do**. Nhớ lựa chọn; lỗi → tự về mặc định |

> Đã loại: đọc PDF. `core/document_reader.py` giữ nguyên `.docx`/`.txt`, chỉ bổ sung `.srt`/`.vtt` ở mục 2.6.

---

## 4. ĐỢT 3 — P2 → `v3.3.0` (1.5–2 tuần)

### 4.1 Hội thoại / podcast nhiều giọng

- Script định dạng `Tên nhân vật: nội dung` (mỗi dòng 1 lượt nói).
- UI: tab **Hội thoại** — bảng ánh xạ nhân vật → giọng (25 preset + giọng tùy chỉnh).
- Engine: nhóm lượt nói theo giọng → `vieneu.infer_batch(texts, voice=X)` (CPU chạy tuần tự) → ghép lại **đúng thứ tự gốc** + pause-pad chuẩn → `TimelineMap` → xuất MP3/WAV + .srt.

### 4.2 Đa nền tảng (Linux + macOS)

Code hiện tại **không có API Windows-specific** (đã grep: không `os.startfile` / `winreg` / `subprocess`) → chủ yếu là đường dẫn & build.

- **`core/paths.py` refactor** (thay đổi lớn nhất):
  - `app_dir()` — thư mục bundle (read-only) → giữ cho logo/datas.
  - `data_dir()` **mới** — nơi ghi được: Windows `%LOCALAPPDATA%\PhanMemTTS\`, Linux `~/.local/share/phanmemtts/`, macOS `~/Library/Application Support/PhanMemTTS/`.
  - `models_dir()` — thứ tự tìm: `app_dir()/models` → `data_dir()/models`.
  - Chuyển `models/voice_config.json`, `test_text.json`, `custom_voices.json`, history, settings, dictionary → `data_dir()`.
  - `HF_HUB_CACHE` cũng chuyển sang `data_dir()` (trên Linux `/opt` thường read-only).
- **Build**:
  - `packaging/build_linux.sh` → `.deb` hoặc AppImage; deps: `libasound2`, `libgomp1`, `python3-tk`.
  - `packaging/build_macos.sh` → `.app` + `.dmg`; `sounddevice` cần `libportaudio`.
  - `.github/workflows/build.yml` — matrix `windows-latest / ubuntu-latest / macos-latest` → artifact mỗi OS.
- **Tương thích ngược**: bản Windows cũ đọc `models/` cạnh EXE → giữ nguyên hành vi (không phá bản đã phát hành).

### 4.3 Điều khoản & Quyền riêng tư

- File mới: `DIEU-KHOAN.md`, `PRIVACY.md`, `THIRD-PARTY-NOTICES.md` (VieNeu-TTS Apache-2.0, ONNX Runtime, librosa, num2words…).
- **Dialog đồng ý lần đầu** → lưu cờ `terms_accepted_at` trong `data_dir()/settings.json`.
- **Checkbox bắt buộc khi tạo giọng mới** (tab "Tạo giọng mới" trong `ui/components/voice_manager.py`): "Tôi cam kết đây là giọng của chính tôi hoặc tôi có quyền sử dụng" → ghi vào metadata của file giọng.
- Copy 3 file vào `dist/` khi build + nhúng trong HDSD.

---

## 5. Quy ước chung mỗi đợt

1. Bump `version.py` (`3.0.0` → `3.1.0` → `3.2.0` → `3.3.0`) và cập nhật `docs/gen_hdsd_v3.py` → sinh HDSD mới.
2. Chạy `pytest tests/` + `app_v3_probe.spec` (smoke-test TTS trong môi trường frozen) trước khi đóng gói.
3. `build_v3.bat` → `dist/` → `packaging/make_zip_v3.ps1` → file phát hành.
4. Commit theo từng hạng mục nhỏ, message dạng `v3.1.0:<nội dung>` (đúng convention repo hiện tại).

---

## 6. Rủi ro

| # | Rủi ro | Xử lý đề xuất |
|---|---|---|
| R1 | `data_dir()` đổi → **mất cấu hình/giọng tùy chỉnh** của bản Windows cũ | Migration: lần chạy đầu copy từ `app_dir()/models/*.json` sang `data_dir()` nếu chưa có; giữ fallback đọc cả 2 nơi |
| R2 | INT8 trên CPU không có VNNI → audio lỗi | Chặn + cảnh báo trước khi chọn; giữ fp32 mặc định |
| R3 | SRT dubbing: câu quá dài vẫn lấn → lệch phụ đề | Xuất kèm `.srt` đã chỉnh mốc + tooltip giải thích trong UI (giống CIT) |
| R4 | `infer_batch` trên CPU tuần tự → hội thoại không nhanh hơn | Chấp nhận; chỉ lợi trên GPU. Ghi rõ trong UI |
| R5 | Build macOS: notarize/quarantine → user phải "Open Anyway" | Chấp nhận (giống CIT); ghi trong HUONG_DAN |
| R6 | macOS `~/Library` + model 600MB → tốn dung lượng | Cho phép xóa model tạm qua Cài đặt |

---

## 7. CÂU HỎI CẦN CHỐT (mặc định khuyến nghị trong ngoặc)

| # | Câu hỏi | Khuyến nghị |
|---|---|---|
| Q1 | Bộ nhớ: bật chế độ **disk-backed** ngay ở P0, hay P0 chỉ fix O(n²) trong RAM? | **Cả hai ở P0** — disk-backed chỉ ~120 dòng và là thứ duy nhất đạt được "không giới hạn độ dài" như CIT |
| Q2 | INT8: mặc định `fp32` hay `int8`? | **`fp32`** (an toàn, giống hiện tại) + nút tải INT8, giống CIT |
| Q3 | Đường dẫn dữ liệu: đồng ý chuyển `voice_config.json` / `custom_voices.json` / history / settings sang `%LOCALAPPDATA%\PhanMemTTS\`? | **Có**, kèm migration tự động — nếu không thì bản Linux/macOS không ghi được config |

---

## 8. NHÁN VỮA (không triển khai)

- ❌ Đọc PDF (loại khỏi P1)
- ❌ API server / FastAPI / `/docs` / OpenAPI (loại khỏi P2)
- ❌ Truy cập LAN + API key `X-API-Key` (loại khỏi P2)
- ❌ Ngôn ngữ nước ngoài / Supertonic 3
- ❌ Tính năng: đồng bộ phụ đề `.vtt` đầu ra, watermark nhãn "AI-generated" (VieNeu đã có `apply_watermark` mặc định)

---

## 9. GHI CHÚ KỸ THUẬT THAM CHIẾU

### 9.1 Benchmark VieNeu v3 Turbo (từ README upstream `pnnbao97/VieNeu-TTS`)

| Backend | RTF | TTFA | Ghi chú |
|---|---|---|---|
| CPU fp32 (mặc định hiện tại) | 0.55–0.62 | 260–400 ms | load ~19s |
| CPU int8 (cần VNNI) | 0.35–0.37 | 140–195 ms | load ~14s |
| GPU (PyTorch/CUDA) batched | 0.011–0.02 | ~115 ms | 16 stream đồng thời |

### 9.2 Tham số SDK quan trọng (`vieneu==3.8.3`)

- `Vieneu(mode="v3turbo", precision="fp32"|"int8", threads=0, device="auto", backend="auto")`
  → `device="auto"` tự chuyển sang PyTorch/GPU nếu có CUDA.
- `infer(text, voice=..., ref_audio=..., denoise=..., max_chars=256, ...)` — **không có** param `speed`.
- `infer_batch(texts, voice=...)` — **tất cả text dùng chung 1 giọng** → hội thoại nhiều giọng phải nhóm theo giọng rồi ghép lại.
- `infer_stream(text, voice=...)` — generator chunk, CPU 1 stream.
- `add_voice(name, ref_audio, denoise=True)` → trả `speaker_emb` + `codes`.
- `save_voices()` / `remove_voice(name)` — persist giọng.
- Model tải về `HF_HUB_CACHE`; bản fp32 đã có trong `models/vieneu/hf_cache/` (`onnx_update/`), **`onnx_int8/` chưa có** → cần tải thêm.

### 9.3 Cấu trúc code hiện tại

```
main.py                  # entry point
core/
  paths.py               # app_dir() / resource_path()   → SẼ refactor ở P2
  models.py              # VoiceModelInfo, SentenceItem, TimelineMap, TrackSegment, MusicMergeConfig
  document_reader.py     # read_document() (.docx/.txt)
  text_processor.py      # split_sentences() + clean_text()
  text_normalizer.py     # normalize_numbers_vi()
engine/
  model_manager.py       # scan() / load_tts() / unload()
  tts_engine.py          # TtsEngine.synthesize_stream() — pause-pad + fade mép
  vieneu_engine.py       # VieneuTTS, PRESET_VOICES, giọng di động .json
audio/
  buffer.py              # (MỚI) GrowableBuffer
  temp_store.py          # (MÓI) memmap disk-backed
  player.py              # AudioPlayer (sounddevice stream)
  exporter.py            # export mp3/wav
  mixer.py               # ghép nhạc nền / intro / outro / crossfade
  speed.py               # apply_speed() — librosa time-stretch + bù RMS
  subtitles.py           # (MỚI) write_srt()
ui/
  main_window.py         # điều phối
  config.py              # voice_config.json, test_text.json  → thêm app_settings.json
  theme.py
  components/
    topbar.py  sidebar.py  playback_bar.py  sync_textbox.py
    voice_manager.py  merge_dialog.py  segment_timeline.py  waveform_timeline.py
    settings_dialog.py   # (MỚI) Cài đặt: precision / threads / storage / model
packaging/               # probe_entry.py, make_full_voice_config.py, make_zip_v3.ps1
docs/                    # gen_hdsd_v3.py, HDSD docx
tools/tao_giong.py       # CLI tạo file giọng di động
```

### 9.4 Lệnh build & kiểm thử

```bash
# dev
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe -m pytest tests/

# probe TTS trong môi trường frozen (không mở GUI)
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm app_v3_probe.spec
dist\AppV3_Probe\AppV3_Probe.exe

# đóng gói bản phát hành
build_v3.bat
powershell -ExecutionPolicy Bypass -File packaging\make_zip_v3.ps1
```

---

## 10. NHẬT KÝ TRIỂN KHAI

### 10.1 Đợt 1 — P0 (xong, phiên bản 3.1.0)

**Quyết định đã chốt (theo khuyến nghị):**
- Q1 → làm **cả hai**: fix O(n²) trong RAM + chế độ lưu **disk-backed** (file tạm PCM16).
- Q2 → mặc định **fp32**, có nút tải INT8 + cảnh báo CPU không hỗ trợ VNNI.
- Q3 → thêm `data_dir()` (theo OS) cho **cấu hình**; `models/` vẫn nằm cạnh EXE (chuyển hẳn sang P2).

**File mới**
| File | Vai trò |
|---|---|
| `audio/buffer.py` | `GrowableBuffer` — mảng float32 tăng dần, `append()` O(len), `view()`/`read()` không copy |
| `audio/temp_store.py` | `TempAudioStore` (PCM16 trên đĩa) + `TempSession` + `should_use_disk()` |
| `audio/peaks.py` | `compute_peaks(source, n)` — đọc qua source (RAM/đĩa) để vẽ waveform |
| `engine/setup_tools.py` | Tải model INT8, cài PyTorch CUDA, dò năng lực CPU (VNNI) |
| `ui/components/settings_dialog.py` | Dialog Cài đặt: precision / threads / GPU / chế độ lưu |
| `tests/` + `pytest.ini` | 24 unit test (buffer, temp store, normalizer, text processor, timeline) |
| `packaging/probe_p0.py` | Probe lõi TTS + store RAM/đĩa |
| `packaging/probe_ui_flow.py` | Probe luồng chuyển đổi thật trong UI (3 ca: RAM / đĩa / bài dài) |

**File sửa**
| File | Thay đổi |
|---|---|
| `audio/player.py` | Chuyển sang "source" (`total_samples` + `read`) — không copy mảng; thêm `ArraySource`; không crash khi không có thiết bị âm thanh |
| `audio/exporter.py` | Thêm `export_source()` — xuất theo block từ source (MP3 không dùng subtype PCM_16) |
| `core/paths.py` | Thêm `data_dir()` theo OS (Windows/macOS/Linux) |
| `core/text_processor.py` | **Fix bug**: dấu "." viết tắt không được nuốt mất dấu xuống dòng phía sau |
| `engine/model_manager.py` | `precision`/`threads`/`device`; `set_runtime()`; bỏ nhánh model Kokoro/ONNX legacy đã chết |
| `engine/vieneu_engine.py` | Truyền `threads` xuống SDK (`Vieneu(precision=…, threads=…)`); bỏ tham số `speed` chết; export `HF_CACHE_DIR` |
| `ui/config.py` | Thêm `app_settings.json` (precision/threads/storage/gpu) trong `data_dir()` |
| `ui/main_window.py` | Viết lại theo kiến trúc store: `_base_store` (1.0x) + `_play_store` (đã áp speed), alias khi speed = 1.0; export/speed/timeline qua source; throttle vẽ waveform; áp speed treo sau khi chuyển đổi xong |
| `ui/components/topbar.py` | Thêm nút ⚙ Cài đặt |
| `ui/components/waveform_timeline.py` | Thêm `set_source()` — vẽ waveform từ source không copy |
| `requirements.txt` | Thêm `librosa` (thiếu → time-stretch fail im lặng), `pytest`, khai báo rõ |
| `build_v3.bat` | Copy `DIEU-KHOAN.md`/`PRIVACY.md`/`THIRD-PARTY-NOTICES.md` nếu có (chuẩn bị cho P2) |
| `version.py` | 3.0.0 → 3.1.0 |

**Lỗi phát hiện & sửa thêm (ngoài kế hoạch)**
1. `core/text_processor.py` — chữ viết tắt cuối câu nuốt mất newline → câu bị gộp.
2. `audio/exporter.py` — `SoundFile(format="MP3", subtype="PCM_16")` không hợp lệ → lỗi xuất MP3.
3. `audio/temp_store.py` — Windows không xoá được file đang mở → `TempSession` phải đóng store trước khi xoá thư mục.
4. `ui/main_window.py` — đổi tốc độ **trong lúc** chuyển đổi: status hứa "áp sau" nhưng không áp → nay áp tự động khi xong.
5. `audio/player.py` — không có sound card thì `OutputStream` ném exception → nay degrade (vẫn xuất file được).
6. `audio/player.py` — store lớn lên (chế độ đĩa) thì không ai chuyển player khỏi BUFFERING → status "Hoàn tất!" bị ghi đè, app treo.
7. `audio/temp_store.py` — **nghiêm trọng**: player đọc và worker ghi dùng chung 1 file handle → `seek()` của reader làm lệch vị trí ghi → file chỉ còn **1/2 dữ liệu**. Sửa bằng 2 handle riêng (ghi/đọc).
8. `audio/temp_store.py` — thêm `cleanup_stale_sessions()` dọn file tạm còn sót khi app bị tắt đột ngột.

**Kết quả kiểm thử**
- `pytest`: **25/25 pass**.
- `packaging/probe_p0.py`: nạp model 7s, tổng hợp 2 câu, store RAM/đĩa khớp nhau, xuất WAV OK, timeline scale OK.
- `packaging/probe_ui_flow.py`: **KẾT QUẢ: OK** (3 ca)

| Ca | Thời gian tổng hợp | Audio | RAM | Xuất file | Đổi tốc độ 1.5× |
|---|---|---|---|---|---|
| RAM, bài ngắn | 12.6s | 3 câu / 11.6s | 1 380 MB | 114 KB MP3 ✓ | 11.6s → 7.75s ✓ |
| Đĩa, bài ngắn | 7.4s | 3 câu / 11.1s | 1 511 MB | 111 KB MP3 ✓ | 11.1s → 7.43s ✓ |
| **Đĩa, bài dài** | 91.1s | **36 câu / 139.8s** | **1 740 MB** | 1.39 MB MP3 ✓ | 139.8s → 93.2s ✓ |

> RAM không tăng theo độ dài audio (chỉ +160 MB cho 2.3 phút audio) → bài 2 giờ không còn nhân 3 bản trong RAM như bản v3.0.0.
> File audio tạm được dọn sạch sau khi đóng app ✓

- Build frozen (`app_v3_probe.spec`): 26 giọng, nạp model 8.5s, tổng hợp + xuất MP3 ✓
  (`librosa`/`numba`/`soxr` có trong `_internal` → time-stretch chạy được trong bản EXE).

**Commit:** `8cad5c2` — `v3.1.0: P0 - bo nho O(n^2) + che do luu dia, cai dat INT8/threads/GPU, 25 unit test, probe UI`

**Còn lại (không chặn P0)**
- Đo RAM thực tế với bài ~2 giờ (ước tính hiện tại: ~1.8 GB, không đổi theo độ dài).
- Build `build_v3.bat` + đóng gói bản phát hành v3.1.0 khi chốt phát hành.

### 10.2 Đợt 1b — Sửa lỗi "chuyển sang INT8 báo kiểm tra kết nối internet"

**Triệu chứng:** chọn INT8 trong Cài đặt → lúc chuyển đổi báo
`LocalEntryNotFoundError: ... Please check your connection and try again or make sure your Internet connection is on.`

**Nguyên nhân (đã tái hiện):**
1. `engine/vieneu_engine.py` đặt `HF_HUB_OFFLINE=1` khi cache đã có model → app cứng offline.
2. `huggingface_hub` đọc biến này **lúc import** → `snapshot_download()` chạy offline
   → **tải im lặng, không tải gì cả** nhưng hàm vẫn trả về thành công → UI báo "Đã tải xong" (báo sai).
3. Chuyển INT8 → `hf_hub_download(..., subfolder="onnx_int8")` không có trong cache →
   `LocalEntryNotFoundError` với thông báo tiếng Anh gây hiểu nhầm.

**Đã sửa:**
| File | Thay đổi |
|---|---|
| `engine/setup_tools.py` | Thêm `online_window()` — tạm bật mạng (sửa cả `os.environ` **và** `huggingface_hub.constants.HF_HUB_OFFLINE`) rồi khôi phục. `download_int8()` **kiểm chứng** sau khi tải (đủ 7 file `onnx_int8/*`) mới báo thành công, không có thì ném lỗi rõ ràng. `int8_installed()` kiểm đủ 7 file. Thêm `INT8_FILES`. |
| `engine/vieneu_engine.py` | `_friendly_load_error()` — đổi lỗi "thiếu file trong cache" thành thông báo tiếng Việt có hướng dẫn cụ thể. |
| `ui/components/settings_dialog.py` | Chọn INT8 mà chưa tải → làm nổi nút "Tải model INT8 (bắt buộc)" + cảnh báo màu đỏ; cập nhật ngay khi đổi precision. |
| `tests/test_setup_tools.py` | 4 test mới (online_window khôi phục state, int8_installed cần đủ file, thông báo lỗi). |

**Kết quả kiểm thử:**
- Tải thật: 7 file / 158 MB trong **20.9s** → `int8_installed() = True` → `HF_HUB_OFFLINE` về lại `1` ✓
- Nạp INT8 **offline**: 6.0s, tổng hợp 3.28s audio, peak 0.782 ✓
- FP32 vẫn chạy bình thường (8.1s) ✓
- Thiếu file INT8 → thông báo mới: *"Chưa tải model INT8 trên máy này. Mở ⚙ Cài đặt → bấm «Tải model INT8»…"* ✓
- `pytest`: **29/29 pass** ✓

**Lưu ý máy này:** CPU Intel Comet Lake (Model 140) — **không có VNNI** → INT8 có thể tiếng nhiễu.
UI đã cảnh báo; khuyến nghị vẫn dùng FP32.
