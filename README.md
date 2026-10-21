# Phần Mềm Đọc Văn Bản Offline

Ứng dụng đọc văn bản thành giọng nói tiếng Việt, chạy hoàn toàn offline trên CPU.

Phiên bản hiện tại: **v3.1.0**

## Tính năng

- **Engine TTS VieNeu v3 Turbo**: 48 kHz, 25 giọng preset, chạy offline CPU (ONNX Runtime)
- **Chọn độ chính xác model**: FP32 (mặc định) hoặc **INT8** (nhanh ~1.6×, nhỏ ~4× — nút tải trong Cài đặt)
- **Tuỳ chọn số luồng CPU** và **cài hỗ trợ GPU** (PyTorch/CUDA) trong Cài đặt
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
├── core/                   # Text processing, models, đường dẫn
├── engine/                 # TTS engine (VieNeu) + công cụ cài đặt
├── audio/                  # Buffer, player, exporter, mixer, time-stretch
└── ui/                     # CustomTkinter UI
```

## Cài đặt (trong app)

Bấm **⚙ Cài đặt** trên thanh trên cùng:

| Mục | Ý nghĩa |
|---|---|
| Độ chính xác | `FP32` (chất lượng cao, mặc định) hoặc `INT8` (nhanh hơn, cần CPU có VNNI) |
| Số luồng CPU | 0 = tự động, hoặc chỉ định 2/4/6/8 luồng |
| Cài hỗ trợ GPU | Tải PyTorch CUDA → app tự dùng GPU sau khi khởi động lại |
| Bộ nhớ | `Tự động` / `Luôn trong RAM` / `Luôn ghi file tạm` |

Cấu hình lưu tại `%LOCALAPPDATA%\PhanMemTTS\app_settings.json`.

### INT8 và GPU

- **INT8**: model nằm ở thư mục `models/vieneu/hf_cache/`, tải qua nút **Tải model INT8**
  (khoảng 150 MB, cần mạng một lần). CPU cần hỗ trợ **VNNI** (Intel thế hệ 11+ / AMD Zen 3+),
  nếu không thì audio có thể bị nhiễu — hãy nghe thử trước.
- **GPU**: nút **Cài hỗ trợ GPU** tải PyTorch bản CUDA (vài GB, cần ≥ 12 GB trống).
  Sau khi cài, khởi động lại app — VieNeu tự chuyển sang backend GPU (nhanh hơn ~25×).

## Yêu cầu

- Python 3.10+
- Windows 10/11
- ~1GB RAM (bài dài dùng chế độ đĩa nên RAM gần như không đổi)

## Chạy thử

```bash
.venv\Scripts\python.exe -m pytest              # unit test
.venv\Scripts\python.exe packaging\probe_p0.py   # probe lõi TTS + store RAM/đĩa
.venv\Scripts\python.exe packaging\probe_ui_flow.py  # probe luồng chuyển đổi trong UI
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
