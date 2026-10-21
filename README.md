# Phần Mềm Đọc Văn Bản Offline

Ứng dụng đọc văn bản thành giọng nói tiếng Việt, chạy hoàn toàn offline trên CPU.

## Tính năng

- **Engine TTS VieNeu v3 Turbo**: 48kHz, 25 giọng preset, chạy offline CPU
- Sidebar hiện đại, quản lý giọng đọc bằng checkbox
- Test giọng nhanh với câu tùy chỉnh
- Đọc streaming từng câu, highlight câu đang phát
- Xuất file MP3/WAV
- Hỗ trợ .docx / .txt

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
├── core/                   # Text processing, models
├── engine/                 # TTS engine (VieNeu)
├── audio/                  # Player, exporter
└── ui/                     # CustomTkinter UI
```

## Yêu cầu

- Python 3.10+
- Windows 10/11
- ~1GB RAM

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

