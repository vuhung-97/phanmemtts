# Phần Mềm Đọc Văn Bản Offline

Ứng dụng đọc văn bản thành giọng nói tiếng Việt, chạy hoàn toàn offline trên CPU.

## Tính năng

- **2 engine TTS**: VieNeu v3 Turbo (48kHz, 25 giọng) + Kokoro-Vietnamese (24kHz, 13 giọng)
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
├── download_model.py       # Tải model Kokoro + VieNeu
├── requirements.txt
├── core/                   # Text processing, models
├── engine/                 # TTS engines (Kokoro, VieNeu)
├── audio/                  # Player, exporter
└── ui/                     # CustomTkinter UI
```

## Yêu cầu

- Python 3.10+
- Windows 10/11
- ~1GB RAM
