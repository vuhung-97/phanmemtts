# Phần Mềm Đọc Văn Bản Offline

Ứng dụng đọc văn bản thành giọng nói tiếng Việt, chạy hoàn toàn offline trên CPU.

Phiên bản hiện tại: **v3.2.0**

## Tính năng

- **Engine TTS VieNeu v3 Turbo**: 48 kHz, 25 giọng preset, chạy offline CPU (ONNX Runtime)
- **Chọn độ chính xác model**: FP32 (mặc định) hoặc **INT8** (nhanh hơn ~20–30% — có sẵn trong bản cài)
- **Tuỳ chọn số luồng CPU** trong Cài đặt
- Sidebar hiện đại, quản lý giọng đọc bằng checkbox
- Test giọng nhanh với câu tùy chỉnh
- Đọc streaming từng câu, highlight câu đang phát (karaoke)
- **Waveform timeline** dạng sóng + dải mốc câu, tua nhanh theo câu
- Xuất file MP3/WAV
- Hỗ trợ .docx / .txt
- **Đổi tốc độ 0.5x–2.0x ngay khi đang phát** (time-stretch giữ cao độ + bù âm lượng), không cần tổng hợp lại
- **Ghép nhạc**: nhạc nền lặp + intro/outro + crossfade, có preview
- **Tạo giọng mới từ file mẫu** (wav/mp3) và chia sẻ giọng qua file `.json` sang máy khác
- **Chế độ lưu âm thanh linh hoạt**: RAM (bài ngắn) hoặc file tạm trên đĩa (bài dài — không tốn RAM)
- **Thẻ cảm xúc + thẻ nghỉ trong văn bản**: `[cười]`, `[thở dài]`, `[hắng giọng]`, `[nghỉ 3s]` — có thanh chèn nhanh ngay trên khung soạn thảo
- **Lịch sử bản dựng**: mỗi lần xuất file được lưu bản sao; nghe lại / mở thư mục / xoá ngay trong app
- **Menu bar kiểu Windows**: `Tệp` / `Công cụ` / `Trợ giúp` với phím tắt (Ctrl+O, Ctrl+H, Alt+F/C/T); hai nút hành động chính `⚡ Chuyển đổi` + `💾 Xuất file` nằm cố định ở panel phải

## Menu

| Menu | Mục | Phím tắt |
|---|---|---|
| **Tệp** | Mở văn bản… | `Ctrl+O` |
| | Thoát | `Alt+F4` |
| **Công cụ** | Ghép nhạc | |
| | Lịch sử bản dựng | `Ctrl+H` |
| | Cài đặt | |
| **Trợ giúp** | Hướng dẫn sử dụng | |
| | Giới thiệu | |

`Alt+F` / `Alt+C` / `Alt+T` mở nhanh menu tương ứng. Khi đang chuyển đổi, mục
**Ghép nhạc** và **Cài đặt** bị khoá (đổi cấu hình giữa lúc đọc sẽ nạp lại model);
**Lịch sử** vẫn mở được.

## Thẻ trong văn bản

Gõ thẻ ngay trong câu (có thanh **Chèn nhanh** phía trên khung soạn thảo):

| Thẻ | Tác dụng |
|---|---|
| `[cười]` | Model tự đọc thành tiếng cười (bản tiếng Anh: `[chuckle]`) |
| `[thở dài]` | Tiếng thở dài (`[sigh]`) |
| `[hắng giọng]` | Tiếng hắng giọng (`[clear throat]`) |
| `[nghỉ 3s]` | Chèn **đúng 3 giây** khoảng lặng (app tự cắt câu, không phụ thuộc model) |
| `[nghỉ]` | Nghỉ mặc định 2 giây |

Thẻ nghỉ nhận `s` / `giây` / `ms`, số thập phân bằng dấu phẩy hoặc dấu chấm
(`[nghỉ 1,5s]`, `[nghỉ 500ms]`), tự kẹp trong 0.1–30 giây.

> Đặt thẻ **trong câu**, đừng để thẻ đứng riêng một dòng — câu chỉ có thẻ cảm xúc
> dễ ra tiếng lạ. Thẻ không nhận diện được (ví dụ `[abc]`) sẽ bị đọc thành chữ;
> thanh chèn nhanh cảnh báo ngay khi bạn gõ.

## Lịch sử bản dựng

Mỗi lần **💾 Xuất file** thành công, app sao chép file vào
`%LOCALAPPDATA%\PhanMemTTS\history\<id>\audio.mp3` và ghi `index.json`.

Bấm **Công cụ → Lịch sử bản dựng** (`Ctrl+H`) để xem, **▶ Nghe** (mở bằng trình
phát mặc định), **📂** mở thư mục, **🗑** xoá bản ghi.

- Xoá trong lịch sử chỉ xoá **bản sao** — file bạn đã xuất ra ngoài vẫn còn.
- Cảnh báo khi vượt **500 MB**; tự xoá bản cũ nhất khi vượt **1 GB** (tối đa 200 bản).

## Cài đặt

```bash
git clone https://github.com/vuhung-97/phanmemtts.git
cd phanmemtts
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python download_model.py
python main.py
```

## Cấu trúc

```
├── main.py                 # Entry point
├── download_model.py       # Tải model VieNeu
├── requirements.txt
├── core/                   # Text processing, thẻ, lịch sử, models, đường dẫn
├── engine/                 # TTS engine (VieNeu) + công cụ cài đặt
├── audio/                  # Buffer, player, exporter, mixer, time-stretch
└── ui/                     # CustomTkinter UI
```

## Cài đặt (trong app)

Bấm **⚙ Cài đặt** trên thanh trên cùng:

| Mục | Ý nghĩa |
|---|---|
| Độ chính xác | `FP32` (chất lượng cao, mặc định) hoặc `INT8` (nhanh hơn ~20–30%, cần CPU có VNNI) |
| Số luồng CPU | 0 = tự động, hoặc chỉ định 2/4/6/8 luồng |
| Bộ nhớ | `Tự động` / `Luôn trong RAM` / `Luôn ghi file tạm` |

Cấu hình lưu tại `%LOCALAPPDATA%\PhanMemTTS\app_settings.json`.

### Offline và INT8

App chạy **100% offline**: không có bất kỳ request mạng nào (`HF_HUB_OFFLINE=1` +
`HF_HUB_DISABLE_TELEMETRY=1`). Toàn bộ model — gồm cả **FP32 và INT8** — được chép sẵn
trong `models/vieneu/hf_cache/` của bản phát hành, nên không có nút tải về.

- **INT8**: chọn trong ⚙ Cài đặt, dùng ngay (không cần tải). CPU cần hỗ trợ **VNNI**
  (Intel thế hệ 11+ / AMD Zen 3+); nếu không thì audio có thể bị nhiễu — hãy nghe thử trước.
- **GPU**: không hỗ trợ. Bản phát hành chỉ chạy CPU (không kèm PyTorch).
- Nếu bộ cài thiếu file (copy thiếu, antivirus cách ly…), app báo **đúng tên file thiếu**
  và hướng dẫn chép lại thư mục `models/` — không hiện lỗi mạng gây hiểu nhầm.

## Yêu cầu

- Python 3.10+
- Windows 10/11
- ~1GB RAM (bài dài dùng chế độ đĩa nên RAM gần như không đổi)

## Chạy thử

```bash
.venv\Scripts\python.exe -m pytest              # unit test
.venv\Scripts\python.exe packaging\probe_p0.py   # probe lõi TTS + store RAM/đĩa
.venv\Scripts\python.exe packaging\probe_ui_flow.py  # probe luồng chuyển đổi trong UI
.venv\Scripts\python.exe packaging\probe_tags_history.py  # probe thẻ cảm xúc/nghỉ + lịch sử
.venv\Scripts\python.exe packaging\probe_menu_toolbar.py  # probe menu bar + panel hành động
```

## Đóng gói (OneDir)

Bản phát hành v3: **Phần mềm chuyển đổi văn bản thành giọng nói tự nhiên v3**

```bash
build_v3.bat
```

Script sẽ:

1. Đóng gói bằng PyInstaller (`app_v3.spec`, OneDir) → `dist/PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3/`
2. Copy `models/` (~607MB, model offline) cạnh EXE — `app_dir()` khi frozen trỏ về thư mục chứa EXE
3. Bật toàn bộ giọng trong `models/voice_config.json` của bản phát hành
4. Copy HDSD + tạo `HUONG_DAN_V3.txt`
5. Nén thành file `.zip` (tùy chọn): `packaging\make_zip_v3.ps1`

Cấu trúc bản phát hành:

```
PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3.exe
_internal/                     # thư viện + logo
models/vieneu/hf_cache/        # model offline ~600MB
models/voice_config.json       # cấu hình giọng (ghi được khi chạy)
HUONG_DAN_V3.txt
```

> Lưu ý: file `.spec` chỉ gói code + thư viện; `models/` phải nằm **cạnh EXE**
> (không đặt trong `_internal/`) vì app ghi cấu hình/giọng tùy chỉnh tại đó.

Kiểm tra đường TTS trong môi trường frozen (console, không mở GUI):

```bash
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm app_v3_probe.spec
dist\AppV3_Probe\AppV3_Probe.exe
```
