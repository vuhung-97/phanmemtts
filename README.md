# Phần Mềm Đọc Văn Bản Offline

Ứng dụng đọc văn bản thành giọng nói tiếng Việt, chạy hoàn toàn offline trên CPU.

Phiên bản hiện tại: **v3.4.0**

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
- **Từ điển phát âm**: thay cách đọc từ viết tắt/tên riêng (`KTX` → `ký túc xá`), có bật/tắt, nhập/xuất tệp
- **Làm sạch văn bản**: bỏ dòng trống thừa + gộp dòng ngắt giữa câu, giữ nguyên công thức/danh sách, hoàn tác bằng `Ctrl+Z`
- **Chuyển đổi hàng loạt**: marker `[P1]`, `[P2]`… → mỗi phần một tệp MP3/WAV, tuỳ chọn đóng gói `.zip`
- **Điều khoản & quyền riêng tư**: đồng ý lần đầu, cam kết quyền sử dụng giọng khi tạo giọng mới
- **Lịch sử bản dựng**: mỗi lần xuất file được lưu bản sao; nghe lại / mở thư mục / xoá ngay trong app
- **Giao diện SaaS**: header (logo + tên + version) + toolbar `Tệp` / `Trợ giúp` + sidebar chức năng (thu gọn được) + thanh phát dùng chung có waveform; mỗi chức năng là một trang riêng, chuyển qua lại không mất trạng thái
- **Bản quyền offline (freemium)**: chưa kích hoạt vẫn **chuyển đổi + nghe thử** được, chỉ khoá **Xuất file** và **Ghép nhạc**; kích hoạt bằng mã 15 ký tự theo từng máy, có dùng thử 7 ngày

## Giao diện

```
Header   : logo + tên phần mềm + version
Toolbar  : Tệp · Trợ giúp        (bên phải: trạng thái + số giọng)
Sidebar  : 5 chức năng chính + 4 công cụ + trạng thái bản quyền
Nội dung : trang của chức năng đang chọn (cuộn được)
Player   : waveform + ⏮ ▶ ⏭ + −5/+5 + thời lượng + tốc độ (hiện khi có audio)
```

| Sidebar | Nội dung | Phím tắt |
|---|---|---|
| 📖 Đọc văn bản | Soạn văn bản, chọn giọng, chuyển đổi, xuất file | `Ctrl+1` |
| 🎭 Hội thoại | Hội thoại nhiều giọng (bản 3.5.0) | `Ctrl+2` |
| 🎵 Ghép nhạc | Intro / nhạc nền / outro, crossfade | `Ctrl+3` |
| 📦 Hàng loạt | Marker `[P1]`, `[P2]`… → nhiều tệp / zip | `Ctrl+4` |
| 🕘 Lịch sử | Bản dựng đã xuất, nghe lại / mở thư mục / xoá | `Ctrl+5` |
| 🔤 Từ điển | Từ điển phát âm | `Ctrl+6` |
| 🎙 Giọng đọc | Bật/tắt, nhập/xuất, tạo giọng | `Ctrl+7` |
| ⚙ Cài đặt | Precision, threads, chế độ lưu | `Ctrl+8` |
| 🔑 Bản quyền | Trạng thái, hạn dùng, nhập mã | `Ctrl+9` |

| Toolbar | Mục | Phím tắt |
|---|---|---|
| **Tệp** | Mở văn bản… · Mở thư mục dữ liệu… · Thoát | `Ctrl+O` / `Alt+F4` |
| **Trợ giúp** | Hướng dẫn sử dụng · Điều khoản sử dụng · Thông tin bản quyền · Giới thiệu | `Ctrl+Shift+L` |

`Alt+F` / `Alt+T` mở nhanh menu Tệp / Trợ giúp. Khi đang chuyển đổi, sidebar và menu bị
khoá (trừ **Lịch sử**); nút chính trong trang đổi thành `⏹ Dừng`.

Thanh **Chèn nhanh** trong trang Đọc văn bản có: thẻ cảm xúc, thẻ nghỉ, **📖 Từ điển**,
**🧹 Làm sạch**.

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

## Từ điển phát âm

`Công cụ → Từ điển phát âm…` (`Ctrl+Shift+D`) hoặc nút **📖 Từ điển**.

- Thay cụm viết tắt/tên riêng trước khi đọc: `KTX` → `ký túc xá`, `TP.HCM` → `thành phố Hồ Chí Minh`.
- Mặc định thay **nguyên từ** (`KTX` không khớp trong `KTXL`); có tuỳ chọn phân biệt hoa/thường.
- Không thay bên trong thẻ `[...]`. Cụm dài được thay trước cụm ngắn.
- Lưu tại `%LOCALAPPDATA%\PhanMemTTS\pronunciation-dict.json`; có bật/tắt, nhập/xuất tệp, tìm kiếm.
- Đổi từ điển sau khi đã chuyển đổi → app nhắc bấm **Chuyển đổi** lại.

## Làm sạch văn bản

`Công cụ → Làm sạch văn bản` (`Ctrl+Shift+K`) hoặc nút **🧹 Làm sạch**.

- Bỏ dòng trống thừa (giữ tối đa 1 dòng trống giữa hai đoạn).
- Gộp dòng bị ngắt giữa câu → model không ngắt hơi sai chỗ.
- **Giữ nguyên** danh sách gạch đầu dòng, số thứ tự, tiêu đề và công thức (`1 + 1 = 2`).
- Hoàn tác bằng `Ctrl+Z`.

## Chuyển đổi hàng loạt

`Công cụ → Chuyển đổi hàng loạt…` (`Ctrl+B`). Đặt marker ở **đầu dòng**:

```
[P1] Bản tin sáng...
[P2] Bản tin trưa...
```

- Mỗi marker → một tệp (`bai_doc_P1.mp3`, `bai_doc_P2.mp3`…).
- Phần trước marker đầu tiên (nếu có) thành `P0`.
- Bỏ tick phần không muốn xuất; chọn MP3/WAV; tuỳ chọn đóng gói **.zip**.
- Cần đã kích hoạt bản quyền (giống **Xuất file**).

## Điều khoản & quyền riêng tư

- Lần chạy đầu hiện hộp **Điều khoản sử dụng & Quyền riêng tư**; phải tick đồng ý để dùng app.
- Xem lại: `Trợ giúp → Điều khoản sử dụng`.
- Tạo giọng mới: bắt buộc tick cam kết đây là giọng của mình hoặc có quyền sử dụng.
- Nội dung đầy đủ: `DIEU-KHOAN.md`, `PRIVACY.md`, `THIRD-PARTY-NOTICES.md` (cạnh file chạy).

## Lịch sử bản dựng
Mỗi lần **💾 Xuất file** thành công, app sao chép file vào
`%LOCALAPPDATA%\PhanMemTTS\history\<id>\audio.mp3` và ghi `index.json`.

Bấm **Công cụ → Lịch sử bản dựng** (`Ctrl+H`) để xem, **▶ Nghe** (mở bằng trình
phát mặc định), **📂** mở thư mục, **🗑** xoá bản ghi.

- Xoá trong lịch sử chỉ xoá **bản sao** — file bạn đã xuất ra ngoài vẫn còn.
- Cảnh báo khi vượt **500 MB**; tự xoá bản cũ nhất khi vượt **1 GB** (tối đa 200 bản).

## Bản quyền & kích hoạt

Bản phát hành dùng **khoá offline theo máy**:

| Trạng thái | Chuyển đổi + nghe thử | Xuất file / Ghép nhạc |
|---|---|---|
| Chưa kích hoạt | ✅ | 🔒 |
| Dùng thử 7 ngày | ✅ | ✅ |
| Đã kích hoạt (7 ngày / 30 ngày / vĩnh viễn) | ✅ | ✅ |

- Lần chạy đầu, app mời **Dùng thử 7 ngày** hoặc nhập mã (đóng được để dùng tiếp ở chế độ giới hạn).
- Mã kích hoạt dài **15 ký tự**, gắn với máy qua `MachineGuid` + serial ổ đĩa; copy sang máy khác không dùng được.
- Nhập mã: gõ trực tiếp, dán clipboard, hoặc chọn file `.lic`. Không cần mạng ở bất kỳ bước nào.
- Xem hạn dùng: `Trợ giúp → Thông tin bản quyền` (`Ctrl+Shift+L`) hoặc bấm nhãn 🔑 trên thanh menu.
- Thông tin bản quyền lưu tại `%LOCALAPPDATA%\PhanMemTTS\license.json` — giữ nguyên khi cập nhật.
- Đổi/thay ổ cứng hoặc cài lại Windows → mã máy đổi, cần xin mã mới.

> Cấp mã: xem `docs/HUONG_DAN_CAP_KEY.md` (tài liệu dành cho chủ phần mềm).

## Tool cấp mã (nội bộ)

- Bản đóng gói: `dist\KeygenTTS\KeygenTTS.exe` (+ `keys\license_secret.bin`, `keys\issued.sqlite`).
- Build lại: `build_keygen.bat` (one-file, ~11 MB, tự kiểm tra không nhúng secret).
- Sổ key: 100 key/trang, sắp xếp mới nhất trước, tìm theo tên/SĐT/mã máy.
- Hướng dẫn đầy đủ: `docs/HUONG_DAN_CAP_KEY.md`.

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
│   └── licensing/          # Mã máy, mã kích hoạt 15 ký tự, store, dùng thử, guard
├── engine/                 # TTS engine (VieNeu) + công cụ cài đặt
├── audio/                  # Buffer, player, exporter, mixer, time-stretch
├── ui/                     # CustomTkinter UI
├── tools/                  # Build/update + keygen (dành cho chủ phần mềm)
└── packaging/probe_*.py    # Probe kiểm thử UI + bản phát hành
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
- Màn hình tối thiểu **1024×700**
- ~1GB RAM (bài dài dùng chế độ đĩa nên RAM gần như không đổi)

## Chạy thử

```bash
.venv\Scripts\python.exe -m pytest              # unit test
.venv\Scripts\python.exe packaging\probe_p0.py   # probe lõi TTS + store RAM/đĩa
.venv\Scripts\python.exe packaging\probe_ui_flow.py  # probe luồng chuyển đổi trong UI
.venv\Scripts\python.exe packaging\probe_tags_history.py  # probe thẻ cảm xúc/nghỉ + lịch sử
.venv\Scripts\python.exe packaging\probe_shell.py          # probe shell SaaS (header/toolbar/sidebar/player)
.venv\Scripts\python.exe packaging\probe_license.py       # probe kích hoạt + freemium + chống clone
.venv\Scripts\python.exe packaging\probe_editor_tools.py  # probe làm sạch + từ điển phát âm
.venv\Scripts\python.exe packaging\probe_batch.py         # probe xuất hàng loạt [P1]/[P2] + zip
.venv\Scripts\python.exe packaging\probe_terms.py         # probe điều khoản + cam kết tạo giọng
.venv\Scripts\python.exe packaging\probe_obfuscated_build.py  # kiểm tra bản phát hành đã obfuscate
```

## Đóng gói (modular + PyArmor)

Bản phát hành v3: **Phần mềm chuyển đổi văn bản thành giọng nói tự nhiên v3**

```bash
build_v3.bat          # build phát hành vào dist/<APP>
build_v3.bat test     # build thử vào build/dist_p4 (models = junction, không copy 607 MB)
```

Pipeline (13 bước):

1. Kiểm tra `.venv`, PyArmor và `tools/license_tool/keys/license_secret.bin`.
2. Copy source (`core/engine/audio/ui/version.py`) → `build/src`.
3. Inject 4 mảnh secret thật vào `build/src` (chỉ tồn tại trong lúc build).
4. `tools/check_code_size.py` — chặn BOM và code object > 32 KB (giới hạn PyArmor free).
5. `pyarmor gen` — obfuscate toàn bộ code app.
6. PyInstaller (`app_v3_modular.spec`) — exe chỉ chứa `main.py` + thư viện.
7. Copy code đã obfuscate + `pyarmor_runtime_000000/` ra cạnh exe.
8. Copy `models/` (bỏ qua nếu đã có) + bật toàn bộ giọng.
9. Copy HDSD / điều khoản.
10. `tools/make_manifest.py` — `manifest.json` (sha256 từng file) + lưu `build/manifests/<ver>.json`.
11. `tools/check_release.py` — chặn secret / key / source chưa obfuscate.
12. `tools/make_update_zip.py` — gói cập nhật nhỏ (nếu có manifest bản trước).
13. Xoá `build/src` (không để secret dạng plaintext).

Cấu trúc bản phát hành:

```
<APP>.exe                     # launcher (~29 MB)
_internal/                    # thư viện
core/ engine/ audio/ ui/      # .py ĐÃ OBFUSCATE (cập nhật = copy đè)
pyarmor_runtime_000000/       # runtime PyArmor
models/vieneu/hf_cache/       # model offline ~600 MB
models/voice_config.json      # cấu hình giọng (ghi được khi chạy)
manifest.json                 # sha256 + version + python/pyarmor
HUONG_DAN_V3.txt
```

> `models/` phải nằm **cạnh EXE** (không trong `_internal/`) vì app ghi cấu hình/giọng tại đó.

### Cập nhật

- Chỉ đổi code → `build/update_<ver>.zip` ~**0,25 MB**.
- Có đổi `.exe` (mọi lần build lại) → ~**29 MB**; vẫn nhỏ hơn nhiều so với gửi cả bộ cài ~1 GB.
- Khách giải nén gói rồi chạy `capnhat.bat`: tự backup → copy → kiểm sha256 → **rollback nếu lỗi** → mở lại app.
- Chỉ khi nâng Python/PyArmor mới cần gửi bộ cài đầy đủ.

Kiểm tra bản phát hành (manifest, obfuscate, secret, khởi động):

```bash
.venv\Scripts\python.exe packaging\probe_obfuscated_build.py
```

