# HƯỚNG DẪN CẤP MÃ KÍCH HOẠT (dành cho chủ phần mềm)

> Tài liệu nội bộ — không gửi cho khách.
> Liên quan: `plan_baomat.md` (thiết kế), `core/licensing/` (mã nguồn), `tools/license_tool/` (công cụ).

---

## 1. Chuẩn bị (làm một lần)

### 1.1 Secret

```powershell
cd D:\WORD\tts_a_Doanh\Phan_mem_doc_van_ban
.venv\Scripts\python.exe tools\license_tool\gen_secret.py
```

- File: `tools\license_tool\keys\license_secret.bin` (32 byte, **không nằm trong git**).
- In ra `fingerprint` (16 hex) — dùng để kiểm tra bản backup.
- **Backup ngay 2 nơi** (USB + password manager). Không gửi qua chat/email, không để trong `dist\`.

> Mất secret: không cấp được mã mới cho bản phát hành hiện tại (mã cũ vẫn chạy).
> Lộ secret: người khác tự sinh được mã hợp lệ.

### 1.2 Kiểm tra bản backup

```powershell
Get-FileHash -Algorithm SHA256 "E:\backup\license_secret.bin"
```

16 ký tự đầu phải trùng fingerprint đã in.

---

## 2. Chạy tool

### 2.1 Bản đóng gói `KeygenTTS.exe` (khuyến nghị)

```
dist\KeygenTTS\
├─ KeygenTTS.exe               ← double-click để mở
├─ keys\license_secret.bin     ← secret (bắt buộc)
├─ keys\issued.sqlite          ← sổ key (tự tạo)
└─ HUONG_DAN_CAP_KEY.md
```

- Không cần Python, không cần repo, không cần mạng.
- Copy **cả thư mục** sang USB / máy khác là chạy được.
- Không tách `KeygenTTS.exe` khỏi thư mục `keys\` — exe không chứa secret nên sẽ báo thiếu.
- Build lại: chạy `build_keygen.bat` (giữ nguyên `keys\issued.sqlite` đang có).

### 2.2 Chạy từ repo (khi đang sửa code)

```powershell
tools\license_tool\keygen.bat
# hoặc
.venv\Scripts\pythonw.exe tools\license_tool\keygen.pyw
```

## 3. Cấp mã cho khách (3 bước)

1. Khách mở app → hộp thoại kích hoạt → bấm **Sao chép** mã máy (10 ký tự, dạng `7K2QF-9M3XA`).
2. Bạn mở tool (xem mục 2 — `dist\KeygenTTS\KeygenTTS.exe` hoặc `tools\license_tool\keygen.bat`):

   - Dán mã máy (nút **Dán**) — dán **cả tin nhắn** khách gửi cũng được, tool tự lấy mã 10 ký tự.
   - Chọn loại: 7 ngày / 30 ngày / Vĩnh viễn / Tuỳ chỉnh N ngày.
   - Nhập tên khách / SĐT / ghi chú (tuỳ chọn).
   - Bấm **Tạo mã kích hoạt**.
3. Bấm **Sao chép** → gửi mã 15 ký tự cho khách (`7K2QF-9M3XA-B8T1Z`), hoặc **Lưu file .lic…** rồi gửi file.
   Sau đó bấm **Ghi vào sổ**.

Khách dán mã vào ô "Mã kích hoạt" → **Kích hoạt**.

### Cách khác: dòng lệnh

```powershell
.venv\Scripts\python.exe tools\license_tool\license_cli.py -m 7K2QF-9M3XA -k 30
.venv\Scripts\python.exe tools\license_tool\license_cli.py -m 7K2QF-9M3XA -k lifetime --record --customer "Nguyễn Văn A"
.venv\Scripts\python.exe tools\license_tool\license_cli.py -m 7K2QF-9M3XA -k custom --days 90
.venv\Scripts\python.exe tools\license_tool\license_cli.py --list
```

`-k`: `7` · `30` · `lifetime` · `custom` (kèm `--days`).

---

## 4. Loại mã

| Loại | Ý nghĩa | Hạn dùng |
|---|---|---|
| 7 ngày | Bản dùng thử trả phí ngắn | Hôm tạo + 7 ngày |
| 30 ngày | Gói tháng | Hôm tạo + 30 ngày |
| Vĩnh viễn | Mua đứt | Không giới hạn |
| Tuỳ chỉnh | Gói N ngày (1–3650) | Hôm tạo + N ngày |

**Hạn tính từ ngày bạn tạo mã**, không phải ngày khách kích hoạt → tạo mã đúng lúc khách thanh toán.

Định dạng hỗ trợ đến **khoảng 03/2038** (12 bit ngày). Sau mốc đó cần định dạng mới.

---

## 5. Sổ key

- File: `tools\license_tool\keys\issued.sqlite` (bản exe: `dist\KeygenTTS\keys\issued.sqlite`).
- Xem trong tool: nút **Xem sổ key**.
  - **100 key / trang**, sắp xếp **mới nhất trước**, nút **◀ Trước** / **Sau ▶**.
  - Ô **Tìm**: gõ tên khách (không cần dấu, không phân biệt hoa thường), SĐT hoặc mã máy
    (có hay không có dấu `-` đều khớp). Enter để tìm, **Xoá lọc** để xem tất cả.
  - Có thể tìm bằng dòng lệnh: `license_cli.py --list --search "nguyen" --page 1`.
- Dùng để: tra khách đã cấp gì, cấp lại khi đổi máy, thống kê.
- **Backup định kỳ** file `issued.sqlite` cùng thư mục `keys/` (chứa cả secret).
- Không có chức năng thu hồi (offline không thu hồi được).

---

## 6. Khi nào cấp lại mã (miễn phí)

| Tình huống | Xử lý |
|---|---|
| Đổi/thay ổ cứng, format ổ, cài lại Windows | Mã máy đổi → cấp mã mới (giữ nguyên hạn nếu còn, hoặc theo thoả thuận) |
| Thay CPU **hoặc** mainboard | Không cần cấp lại — app tự cập nhật dấu vết |
| Thay **cả** CPU và mainboard | App báo "kích hoạt trên máy khác" → xác minh khách rồi cấp mã mới |
| Khách đổi sang máy khác | Cấp mã mới cho máy mới; **không** cấp thêm cho máy thứ hai nếu không thoả thuận |
| Khách nhập sai 10 lần | Chờ 60 giây, không cần can thiệp |

Khi cấp lại, ghi `--reissued-from <id>` (CLI) hoặc ghi chú id cũ vào ô ghi chú (GUI) để dễ tra.

---

## 7. Bảo mật — những điều không được làm

- ❌ Commit `license_secret.bin` hoặc `issued.sqlite` lên git.
- ❌ Gửi secret qua Zalo/email/chat (kể cả cho chính mình).
- ❌ Copy secret vào `dist\<APP>\` hoặc gói cập nhật gửi khách (build script sẽ chặn).
- ❌ Đặt secret ở thư mục đồng bộ công khai (ổ chia sẻ, link public).
- ❌ Gửi **thư mục `dist\KeygenTTS\`** cho bất kỳ ai — trong đó có secret.
- ✅ Chỉ giữ secret trên máy bạn + 2 bản backup ngoại tuyến.
- ✅ Kiểm tra repo vẫn **private** sau mỗi lần đổi quyền.
- ✅ Khi mang tool đi xa: dùng USB riêng, không để trong thư mục chia sẻ/cloud công khai.

---

## 8. Xử lý sự cố

| Khách báo | Nguyên nhân | Cách xử lý |
|---|---|---|
| "Mã này được cấp cho máy khác" | Mã máy đã đổi (đổi ổ/cài lại Windows) hoặc gửi nhầm mã | Yêu cầu khách gửi lại mã máy hiện tại, cấp mã mới |
| "Mã kích hoạt không hợp lệ" | Gõ thiếu/sai ký tự, dán thiếu | Khách bấm "Dán từ clipboard" hoặc nhập file `.lic` |
| "Đã hết hạn" | Quá ngày hết hạn | Cấp mã mới |
| "Nhập sai quá nhiều lần" | Sai 10 lần trong 5 phút | Chờ 60 giây rồi nhập lại |
| "Đồng hồ máy đang bị lùi" | Đồng hồ hệ thống bị chỉnh lùi > 3 ngày | Khách chỉnh lại đồng hồ (Windows: Settings → Time & language) |
| App báo "kích hoạt trên máy khác" dù không đổi máy | Nghi clone ổ đĩa | Xác minh khách, cấp mã mới nếu hợp lệ |
| Không tạo được mã | Thiếu `license_secret.bin` | Chạy `gen_secret.py` (chỉ khi chưa từng có) hoặc phục hồi từ backup |

---

## 9. Liên quan đến build

- `build_v3.bat` chạy `tools\inject_secret.py build\src` để ghi 4 mảnh secret vào cây source tạm **trước khi obfuscate**, sau đó xoá `build\src`.
- Bản build từ repo sạch (không inject) dùng secret giả → mã do tool cấp **không** kích hoạt được. Đây là hành vi đúng.
- `build_keygen.bat` đóng gói tool thành `dist\KeygenTTS\KeygenTTS.exe` (one-file, ~11 MB):
  - tự kiểm tra secret **không** bị nhúng vào exe (`check_release.py`);
  - chạy `KeygenTTS.exe --selftest` rồi so mã với repo để chắc bản exe dùng đúng secret;
  - **giữ nguyên** `dist\KeygenTTS\keys\issued.sqlite` qua các lần build (không xoá sổ key).
- Chạy app từ source (dev) thì app đọc trực tiếp `keys\license_secret.bin` để test được mã thật.
