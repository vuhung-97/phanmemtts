# KẾ HOẠCH BẢO MẬT & BẢN QUYỀN — v3.3.0

> **Trạng thái:** Kế hoạch đã chốt (bản 2) — **chưa code**.
> **Phạm vi:** bản quyền offline (mã máy + mã kích hoạt 15 ký tự), dùng thử 7 ngày, build modular + obfuscate bằng PyArmor free.
> **Bản hiện tại:** `3.2.0` (commit `a4efe46`) · **Bản đích:** `3.3.0`
> **Cập nhật:** 26/10/2026
> **Tài liệu liên quan:** `plan_update.md` (mục 11), `README.md`, `docs/HUONG_DAN_CAP_KEY.md` (tạo ở P3).

## Lịch sử thay đổi kế hoạch

| Bản | Ngày | Thay đổi chính |
|---|---|---|
| 1 | 26/10/2026 | Bản nháp: Ed25519, key 136 ký tự, mã máy 20 ký tự, dung sai 3/4 linh kiện |
| **2** | **26/10/2026** | **Mã kích hoạt 15 ký tự (HMAC, 75 bit)**, mã máy **10 ký tự**, chống clone ổ đĩa, bỏ Ed25519/private key, repo đã chuyển **private** |

---

## 0. Tóm tắt

Hai mục tiêu độc lập nhưng gắn nhau:

1. **Bản quyền offline (freemium)**: chưa kích hoạt vẫn mở app và **chuyển đổi + nghe thử** được, nhưng
   **không xuất được file** và không dùng được **Ghép nhạc**; copy sang máy khác thì mã không hợp lệ.
   Owner cấp mã thủ công bằng cách dán mã máy khách gửi (10 ký tự) và nhận lại mã kích hoạt (15 ký tự).
   Không cần mạng ở bất kỳ bước nào.
2. **Bảo vệ & cập nhật code**: đóng gói **modular như v2** (code `.py` nằm cạnh exe) và **obfuscate bằng PyArmor free**,
   để cập nhật chỉ cần gửi vài trăm KB file thay đổi.

Đánh đổi đã chấp nhận có ý thức: mã 15 ký tự buộc dùng **HMAC đối xứng** (không đủ chỗ cho chữ ký bất đối xứng),
nên secret nằm trong app đã obfuscate — người reverse được app có thể viết keygen.
Bù lại: repo đã private nên thuật toán không công khai, và khách gõ tay được mã.

**Ngoài phạm vi:** chống patch binary tuyệt đối, chống reset trial khi xoá sạch dấu vết, ký số exe (SmartScreen),
thu hồi key đã cấp (offline không làm được).

---

## 1. Quyết định đã chốt

| # | Hạng mục | Quyết định |
|---|---|---|
| 1 | Kênh thời gian | Offline hoàn toàn, dùng đồng hồ hệ thống |
| 2 | Loại key | 7 ngày · 30 ngày (đủ 30×24h) · vĩnh viễn · tuỳ chỉnh N ngày |
| 3 | Đồng hồ lùi | Lùi **> 3 ngày** so với mốc đã thấy → chặn |
| 4 | Fingerprint bind key | **MachineGuid + Volume serial ổ C:** (2 thành phần, 6 byte) |
| 5 | Mã máy khách gửi | **10 ký tự**, 2 nhóm 5 (`7K2QF-9M3XA`) |
| 6 | Chống clone ổ đĩa | `license.json` lưu fingerprint 4 thành phần; chặn khi **cả CPU và mainboard** đều khác |
| 7 | Mã kích hoạt | **15 ký tự**, 3 nhóm 5 (`7K2QF-9M3XA-B8T1Z`) — 75 bit |
| 8 | Cơ chế xác thực | HMAC-SHA256 với secret 32 byte, cắt tag 36 bit |
| 9 | Secret | Sinh 1 lần trên máy owner, **không commit**, inject lúc build thành 4 mảnh |
| 10 | Hạn dùng | `expiry` = số ngày kể từ 01/01/2026 (12 bit, đến ~03/2038); `kind=2` = vĩnh viễn |
| 11 | Nhập key | Gõ 15 ký tự hoặc file `.lic` (nội dung chính là mã 15 ký tự); tự bỏ gạch, `O→0`, `I/L→1`, `U→V` |
| 12 | Chống dò | 10 lần sai / 5 phút → khoá 60 giây |
| 13 | Nơi lưu license | `%LOCALAPPDATA%\PhanMemTTS\license.json` (+ `.state` + `HKCU\Software\PhanMemTTS`) |
| 14 | Dùng thử | 7 ngày, chỉ bắt đầu khi người dùng bấm chọn; lưu 3 nơi + dò dấu vết sử dụng |
| 15 | Chế độ chưa kích hoạt | **Freemium**: vẫn chuyển đổi/nghe thử; khoá **Xuất file** + **Ghép nhạc**; hộp thoại kích hoạt mở 1 lần ở lần chạy đầu |
| 16 | Bảo vệ code | PyArmor **free** (obfuscate `.py` → `.py` mã hoá), tách 2 file > 32 KB |
| 17 | Đóng gói | PyInstaller one-dir modular như v2; code rời cạnh exe |
| 18 | Cập nhật | Zip chỉ gồm file đổi + `pyarmor_runtime_000000` + manifest + `capnhat.bat` (0,25 MB khi đổi code; ~29 MB nếu exe đổi) |
| 19 | Repo | **Private** (xác nhận 26/10/2026) — vẫn không commit secret |
| 20 | Phiên bản | `3.3.0` |

---

## 2. Kiến trúc phát hành (modular + PyArmor)

### 2.1 Cây thư mục phát hành

```
PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3\
├─ PhanMem…v3.exe              ~29 MB    launcher: main.py + thư viện đã freeze
├─ _internal\                  411 MB    Python 3.13 + torch + vieneu + tkinter…
├─ models\                     607 MB    model TTS + voice_config + metadata
├─ core\                                code app — .py ĐÃ OBFUSCATE
│   ├─ paths.py  models.py  tags.py  text_utils.py …
│   └─ licensing\                       fingerprint, shortcode, store, trial, guard
│       ├─ shortcode.py                 mã hoá/giải mã + xác thực mã 15 ký tự
│       └─ _k1.py … _k4.py             4 mảnh secret (giá trị thật chỉ có trong bản build)
├─ engine\  audio\  ui\                  .py đã obfuscate, giữ nguyên cấu trúc
├─ version.py                           obfuscate
├─ pyarmor_runtime_000000\      ~1,5 MB .pyd runtime — ship kèm mỗi lần update
├─ manifest.json                        sha256 từng file + version + abi
└─ HUONG_DAN_V3.txt / .docx
```

- `main.py` **không** nằm rời (freeze trong exe) để không ai sửa được điểm khởi động.
- Toàn bộ package app bị `excludes` khỏi PyInstaller; runtime hook thêm thư mục exe vào `sys.path`.
- `models/` và `_internal/` không bao giờ nằm trong gói cập nhật thường.

### 2.2 Vì sao giữ `.py` cạnh exe

| Lợi ích | Chi tiết |
|---|---|
| Gói update rất nhỏ | Chỉ file đã đổi + runtime PyArmor (~0,4–2 MB thay vì ~1 GB) |
| Không cần cài lại | Copy đè, giữ nguyên `models/`, `_internal/`, license |
| Sửa lỗi nhanh | Build lại 1 module, gửi 1 file, khách chạy `capnhat.bat` |
| Vẫn khó đọc | PyArmor mã hoá bytecode; file `.py` không còn đọc/sửa được |

### 2.3 PyArmor free — giới hạn và cách xử lý

| Hạng mục | Free (trial) | Ảnh hưởng |
|---|---|---|
| Thời hạn dùng | Không hết hạn | ✅ dùng lâu dài |
| Build offline | Có | ✅ |
| Python hỗ trợ | 3.11 – 3.15 | ✅ venv 3.13.5 |
| **Kích thước mỗi code object** | **≤ 32 768 byte** | ❗ phải tách 2 file lớn (mục 3) |
| Ẩn chuỗi (Mix Str) | Không | Chuỗi trong code vẫn trích được khi chạy |
| Đổi tên hàm/biến (RFT/BCC) | Không (chỉ Pro) | Tên hàm vẫn thấy |
| EULA | Miễn phí khi doanh thu < 100 × giá Basic ($52) | Hợp lệ giai đoạn hiện tại |

Lệnh obfuscate:

```
pyarmor gen -O build\obf -r build\src
```

- `-r` đệ quy, **không** dùng `-i` → `pyarmor_runtime_000000` ở cấp gốc, khớp `sys.path` do runtime hook thêm.
- Runtime `.pyd` gắn với **Python 3.13 + phiên bản PyArmor** → ghim `pyarmor==9.2.8`, mỗi gói update ship kèm runtime.
- Nâng Basic/Pro sau này chỉ thêm cờ vào `build_v3.bat`.

---

## 3. Tách file để lọt giới hạn 32 KB

| File hiện tại | File mới | Nội dung chuyển | Mục tiêu |
|---|---|---|---|
| `ui/main_window.py` (37,1 KB, 810 dòng) | `ui/main_window.py` | `__init__`, `_build_ui`, `_tick`, `_on_close`, khung | ≤ 18 KB |
| | `ui/window/convert.py` | `ConvertMixin`: `_start_convert`, `_stop`, worker, xử lý message | ≤ 18 KB |
| | `ui/window/export.py` | `ExportMixin`: `_start_export`, `_export_worker`, `_record_history` | ≤ 12 KB |
| | `ui/window/tools.py` | `ToolsMixin`: `_scan_models`, `_selected_voice`, mở các dialog | ≤ 12 KB |
| `ui/components/merge_dialog.py` (33,9 KB, 734 dòng) | `merge_dialog.py` | Lớp dialog + luồng ghép + validate | ≤ 20 KB |
| | `merge_widgets.py` | Widget hàng track, khối preview/intro/outro | ≤ 18 KB |

Cách làm:
- Mixin thuần, **không định nghĩa `__init__`**, không gọi `super().__init__()` trong mixin.
- `class MainWindow(ConvertMixin, ExportMixin, ToolsMixin, ctk.CTk)` — method **chuyển nguyên văn**, không đổi logic.
- Mục tiêu thực tế: mỗi file **< 25 KB** (code object phình ~10–20% so với source).
- Sau khi tách: `pytest` 83 test + 3 probe cũ phải pass trước khi làm tiếp.

Kiểm tra tự động trong `build_v3.bat`:

```
python tools\check_code_size.py build\src      # dừng build nếu file > 30 KB
```

---

## 4. Mã máy & chống clone

### 4.1 Hai thành phần bind key

| # | Linh kiện | Nguồn đọc | Ghi chú |
|---|---|---|---|
| 0 | MachineGuid | `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` | Duy nhất theo từng bản Windows; đổi khi cài lại Windows |
| 1 | Volume serial ổ C: | `GetVolumeInformationW` (ctypes) trên `%SystemDrive%` | Duy nhất theo lần format ổ |

Hai thành phần này là **duy nhất theo từng máy** (khác với CPU brand / tên mainboard vốn trùng giữa các máy cùng model),
nên bind bằng chúng vừa chính xác vừa không phạt oan khi thay CPU/mainboard.

Đọc lỗi → dùng `"UNKNOWN"` cho thành phần đó (vẫn có hash, giảm độ phân biệt).

### 4.2 Chuẩn hoá & băm

```
raw_i  = " ".join(value.strip().lower().split())
digest = sha256(b"PPMTTS|fp|v1|" + str(i).encode() + b"|" + raw_i.encode("utf-8")).digest()
hash_i = int.from_bytes(digest[:3], "big")        # uint24
```

- **Mã máy** = 6 byte (`hash_0 || hash_1`) → base32 Crockford → **10 ký tự**, 2 nhóm 5.
- **Bind trong key** = 24 bit đầu của `sha256(b"PPMTTS|bind|v1|" + 6_byte)`, gọi là `machine24`.

### 4.3 Định dạng hiển thị

- Base32 **Crockford**: `0123456789ABCDEFGHJKMNPQRSTVWXYZ` (bỏ `I`, `L`, `O`, `U`).
- Mã máy: `7K2QF-9M3XA` (10 ký tự).
- Khi dán vào tool/app: bỏ gạch/khoảng trắng, `O→0`, `I/L→1`, `U→V`, uppercase.

### 4.4 Chống clone ổ đĩa (không tốn bit trong mã)

Kịch bản: clone nguyên ổ Windows sang máy khác → `MachineGuid` + `Volume serial` giữ nguyên → key vẫn hợp lệ.
Bịt bằng fingerprint 4 thành phần lưu **trong license**, không trong key:

| Thời điểm | Hành vi |
|---|---|
| Kích hoạt | Ghi `fp4 = {h0..h3}` (MachineGuid, Volume, CPU brand, mainboard) vào `license.json`, ký HMAC |
| Mỗi lần khởi động | So `fp4` hiện tại với `fp4` đã lưu |
| Chỉ 1 thành phần khác | Cho qua, **cập nhật lại** `fp4` (nâng cấp CPU hoặc mainboard) |
| **Cả CPU và mainboard đều khác** | `clone_detected` → chặn, yêu cầu mã mới |
| MachineGuid hoặc Volume khác | `machine_mismatch` → chặn (key không còn bind đúng máy) |

CPU brand và tên mainboard chỉ dùng để phát hiện clone, **không** tham gia sinh mã → không gây phải cấp lại khi nâng cấp linh kiện.

---

## 5. Mã kích hoạt 15 ký tự

### 5.1 Cấu trúc bit (75 bit)

| Bit | Trường | Ý nghĩa |
|---|---|---|
| 74 | `ver` | `1` = định dạng v1 (các giá trị khác bị từ chối) |
| 73–72 | `kind` | `0` = 7 ngày · `1` = 30 ngày · `2` = vĩnh viễn · `3` = tuỳ chỉnh N ngày |
| 71–60 | `expiry` | Số ngày kể từ 01/01/2026 (0–4095 → dùng đến ~03/2038). `kind = 2` thì bỏ qua |
| 59–36 | `machine24` | 24 bit cắt từ fingerprint bind (MachineGuid + Volume serial) |
| 35–0 | `tag` | 36 bit đầu của HMAC-SHA256 |

- 75 bit → **15 ký tự** base32 Crockford, chia **3 nhóm 5**: `7K2QF-9M3XA-B8T1Z`.
- Không có trường ngày cấp và không có nonce: cùng (kind, expiry, máy) luôn cho cùng một mã.

### 5.2 Sinh và xác thực

**Owner tạo mã** (`keygen`):

```
prefix = (ver << 38) | (kind << 36) | (expiry << 24) | machine24      # 39 bit
tag    = int.from_bytes(hmac_sha256(SECRET, prefix.to_bytes(5, "big"))[:5], "big") >> 4
code   = crockford_b32((prefix << 36) | tag, length=15)
```

**App kiểm tra**:

```
value   = crockford_b32_decode(normalize(input))          # phải đúng 75 bit
prefix  = value >> 36
tag     = value & 0xFFFFFFFFF                              # 36 bit
tag_ok  = hmac.compare_digest(tag, recompute(prefix))
ver_ok  = (prefix >> 38) == 1
bind_ok = ((prefix >> 24) & 0xFFFFFF) == machine24_cua_may_nay
hạn      = so sánh expiry với hôm nay (trừ kind = 2)
```

Bất kỳ bước nào sai → coi như không có key (không "đoán gần đúng").

### 5.3 Chuẩn hoá khi nhập

```
bỏ mọi ký tự ngoài [A-Za-z0-9] → uppercase → O→0, I→1, L→1, U→V
→ giải mã base32 → phải đúng 15 ký tự / 75 bit
```

Thông báo lỗi (tiếng Việt, không lộ chi tiết kỹ thuật):

| Tình huống | Thông báo |
|---|---|
| Sai độ dài / sai ký tự | `Mã kích hoạt không hợp lệ. Vui lòng kiểm tra lại.` |
| Sai tag / bị sửa | `Mã kích hoạt không hợp lệ hoặc đã bị sửa.` |
| Đúng tag, sai máy | `Mã này được cấp cho máy khác.` |
| Quá hạn | `Mã đã hết hạn ngày dd/mm/yyyy.` |
| Nhập sai nhiều lần | `Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau 60 giây.` |

### 5.4 File `.lic` và gói kích hoạt

Nội dung file (để gửi Zalo/email hoặc double-click):

```json
{
  "type": "ppmt-key",
  "ver": 1,
  "code": "7K2QF-9M3XA-B8T1Z",
  "machine": "7K2QF-9M3XA",
  "note": "Nguyễn Văn A – 30 ngày"
}
```

- App chấp nhận: gõ 15 ký tự, dán nguyên nội dung JSON, hoặc chọn file `.lic`.
- Gói kích hoạt tuỳ chọn: `<MÃ>.lic` + `KichHoat.bat` → khách double-click, không phải gõ gì.

### 5.5 Secret (khoá ký HMAC)

| Hạng mục | Chi tiết |
|---|---|
| Sinh | 32 byte ngẫu nhiên, **một lần duy nhất** trên máy owner: `tools/license_tool/keys/license_secret.bin` |
| Git | **Không commit** (`.gitignore`); repo chỉ chứa `_k1..4.py` với giá trị giả |
| Chia mảnh | 4 × 8 byte → `core/licensing/_k1.py` … `_k4.py`; `K = sha256(b"PPMTTS|key|v1|" + f1+f2+f3+f4)` |
| Inject | `tools/inject_secret.py` ghi đè 4 mảnh thật vào `build/src/` **trước khi obfuscate**; xoá `build/src` sau build |
| Keygen | Đọc trực tiếp file secret trên máy owner, không import từ repo |
| Backup | 2 nơi (USB + password manager). **Mất secret = không cấp được mã mới** cho bản phát hành hiện tại |
| Đổi secret | Chỉ khi phát hành bản mới; toàn bộ mã cũ vô hiệu |

Vì repo đã **private**, kẻ tấn công không có thuật toán từ source; muốn tạo keygen phải reverse app đã obfuscate trước.

### 5.6 Rủi ro của mã ngắn (đã chấp nhận)

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| Reverse app → trích secret → keygen | Trung bình | PyArmor chỉ làm chậm; đây là cái giá của mã 15 ký tự |
| Mất secret | Cao | Không cấp được mã mới; phải backup |
| Không có dung sai 3/4 | Trung bình | Đổi ổ/cài lại Windows → cấp lại mã (miễn phí) |
| Không có ngày cấp trong mã | Thấp | UI chỉ hiện hạn dùng |
| Clone ổ đĩa | Thấp | Đã bịt bằng `fp4` trong `license.json` (mục 4.4) |
| Lộ repo | Thấp | Đã private; secret vẫn không nằm trong git |

---

## 6. Lưu trữ & kiểm soát thời gian

### 6.1 `license.json`

Đường dẫn: `%LOCALAPPDATA%\PhanMemTTS\license.json`

```json
{
  "ver": 2,
  "machine": "7K2QF-9M3XA",
  "key": "7K2QF-9M3XA-B8T1Z",
  "fp4": { "guid": 123456, "vol": 234567, "cpu": 345678, "board": 456789 },
  "installed_at": 1793000000,
  "max_seen_utc": 1793000000,
  "fail_count": 0,
  "fail_window": 0,
  "lock_until": 0,
  "state_sig": "<64 hex>"
}
```

- `fp4`: fingerprint 4 thành phần tại lần kích hoạt — dùng phát hiện clone (mục 4.4).
- `fail_count` / `fail_window` / `lock_until`: đếm số lần nhập sai để chống dò.
- `state_sig = HMAC-SHA256(K_state, canon(...))`,
  `K_state = SHA-256(b"PPMTTS|state|v2|" + machine_bytes)` — chỉ là chống sửa vô tình, không phải bảo mật.
- **Hạn dùng luôn tính từ mã đã giải mã**, không bao giờ đọc từ JSON.

### 6.2 Ba nơi lưu mốc thời gian

| Nơi | Nội dung | Mục đích |
|---|---|---|
| `%LOCALAPPDATA%\PhanMemTTS\license.json` | như trên | Nguồn chính |
| `%LOCALAPPDATA%\PhanMemTTS\.state` | `{"last_seen", "trial_start", "fail_count", "lock_until", "sig"}` | Bản sao nhẹ, ghi mỗi 60 s |
| `HKCU\Software\PhanMemTTS` | `LastSeen` (QWORD), `TrialStart` (QWORD), `StateSig` (SZ) | Sống sót khi xoá thư mục |

Khi khởi động: đọc cả 3, lấy **max** của `last_seen`, **min** của `trial_start`, **max** của `lock_until`.

### 6.3 Tính hạn

```
today   = (ngày hiện tại theo max(time.time(), max_seen_utc))
day_exp = expiry                      # số ngày kể từ 01/01/2026
còn hạn ⟺ kind == 2  hoặc  today_index <= day_exp
còn lại = day_exp - today_index       # hiển thị "Còn N ngày"
```

Mốc `today_index = (utcnow.date() - date(2026,1,1)).days`.

### 6.4 Chống lùi giờ

```
if now < max_seen_utc - 3*86400:  → clock_rollback (chặn)
```

- Dung sai 3 ngày cho pin CMOS yếu.
- Lùi ≤ 3 ngày: vẫn chạy, **không** cập nhật `max_seen_utc` xuống.

### 6.5 Trạng thái `guard`

| Trạng thái | Ý nghĩa | Hành vi |
|---|---|---|
| `licensed` | Mã hợp lệ, còn hạn / vĩnh viễn | Vào app, badge |
| `trial` | Đang dùng thử, còn hạn | Vào app, badge "Dùng thử" |
| `expired` | Mã hợp lệ nhưng quá hạn | Chặn, mở ActivationDialog |
| `machine_mismatch` | Mã cấp cho máy khác (Guid/Volume khác) | Chặn |
| `clone_detected` | Guid+Volume khớp nhưng cả CPU và mainboard đều khác | Chặn, yêu cầu mã mới |
| `clock_rollback` | Đồng hồ lùi > 3 ngày | Chặn, thông báo riêng |
| `tampered` | JSON sai chữ ký / sửa mã | Chặn, coi như chưa kích hoạt |
| `rate_limited` | Nhập sai quá nhiều | Chặn tạm, hẹn giờ thử lại |
| `none` | Chưa có gì | Hộp thoại lần đầu |

---

## 7. Dùng thử 7 ngày

- Lần chạy đầu (chưa có license, chưa có trial): hộp thoại hiện 2 lựa chọn, **không tự tính giờ**:
  `🕐 Dùng thử 7 ngày` · `🔓 Tôi có mã kích hoạt`.
- Chỉ khi bấm "Dùng thử" mới ghi `trial_start` vào 3 nơi.
- Hết 7 ngày → khoá **Xuất file + Ghép nhạc** (vẫn chuyển đổi/nghe thử), badge đỏ, mở ActivationDialog.
- **Chống reset**: nếu chưa có dấu vết trial nhưng đã có dấu vết sử dụng (`app_settings.json`, `history\`, `tmp\`)
  → coi như trial đã dùng hết.
- **Migration**: khách nâng cấp từ 3.2.0 (đã có `app_settings.json`) sẽ không được trial → cần cấp mã trước khi phát hành 3.3.0.

---

## 8. Điểm chặn & gia cố

### 8.1 Các điểm chặn (mô hình freemium)

Chưa kích hoạt: app **vẫn mở**, chuyển đổi + phát + nghe thử + quản lý giọng + cài đặt vẫn dùng.
Chỉ khoá phần tạo ra file: **Xuất file** và **Ghép nhạc**.

| # | Vị trí | Hành vi |
|---|---|---|
| 1 | `MainWindow._first_run_prompt` (sau 400 ms) | Lần chạy đầu: mở ActivationDialog (dùng thử / nhập mã); đóng được để dùng tiếp chế độ giới hạn |
| 2 | `_refresh_license_badge()` | Cập nhật badge + đổi nhãn nút thành `🔒 Xuất file` khi chưa kích hoạt |
| 3 | `_start_export()` | Chưa kích hoạt → mở hộp thoại kích hoạt, **không** mở hộp chọn file |
| 4 | `_open_merge_dialog()` | Chưa kích hoạt → mở hộp thoại kích hoạt |
| 5 | `_export_worker()` | Chặn lần 2 (phòng khi gọi trực tiếp) — không ghi file |
| 6 | `_tick` (60 s) | Ghi `max_seen_utc`, cập nhật badge; **không** dừng chuyển đổi khi hết hạn |

### 8.2 Gia cố

- `__assert_armored__()` chéo giữa `core.licensing.guard`, `ui.main_window`, `engine.vieneu_engine`:
  module bị thay bằng bản rỗng → dừng app với thông báo "Bản cài đặt bị thay đổi, vui lòng cài lại".
- 4 mảnh secret nằm ở 4 module riêng, không có literal hoàn chỉnh nào trong source.
- Rate limit 10 lần sai / 5 phút → khoá 60 giây (chống dò tag 36 bit).
- Không có biến môi trường / cờ `--dev` bỏ qua kiểm tra trong bản phát hành;
  máy dev tự cấp mã vĩnh viễn cho máy mình bằng keygen.

### 8.3 Giới hạn đã biết

- Reverse app → keygen (đã chấp nhận, đổi lấy mã 15 ký tự).
- Xoá sạch `%LOCALAPPDATA%` + registry trên máy chưa từng dùng → trial bắt đầu lại.
- Đồng hồ hệ thống là nguồn thời gian duy nhất.
- Exe chưa ký số → SmartScreen có thể cảnh báo lần đầu.

---

## 9. Giao diện

### 9.1 `ui/components/activation_dialog.py` (mới)

Modal ~560 × 440, **không** logo/tên/SĐT/Zalo.

```
┌──────────────────────────────────────────────────────────┐
│  Thiết bị chưa được kích hoạt                            │
│                                                          │
│  Mã máy của bạn                                          │
│  ┌──────────────────────────┐  ┌───────────┐             │
│  │ 7K2QF-9M3XA              │  │ Sao chép  │             │
│  └──────────────────────────┘  └───────────┘             │
│  Gửi mã máy trên cho nhà phát triển để nhận mã kích hoạt.│
│                                                          │
│  Mã kích hoạt (15 ký tự)                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│  [ Dán từ clipboard ]   [ Nhập từ file .lic… ]           │
│                                                          │
│  ⓘ Lỗi (dòng đỏ, chỉ hiện khi có)                        │
│                                                          │
│      [ 🕐 Dùng thử 7 ngày ]      [ 🔓 Kích hoạt ]        │
└──────────────────────────────────────────────────────────┘
```

- "Sao chép" copy: `Mã máy: 7K2QF-9M3XA | Phiên bản: 3.3.0`.
- Ô mã hỗ trợ dán 15 ký tự, dán JSON `.lic`, hoặc chọn file.
- Nút "Dùng thử" ẩn khi trial đã dùng/hết.
- Hiển thị đúng 5 loại lỗi ở mục 5.3 + đếm ngược khi bị khoá 60 giây.

### 9.2 `ui/components/license_dialog.py` (mới)

Mở từ **Trợ giúp → Thông tin bản quyền** (`Ctrl+Shift+L`).

| Dòng | Nội dung |
|---|---|
| Trạng thái | `Đã kích hoạt` / `Dùng thử` / `Hết hạn` |
| Loại | 7 ngày / 30 ngày / Vĩnh viễn / Tuỳ chỉnh |
| Hạn dùng | dd/mm/yyyy hoặc `Không giới hạn` |
| Còn lại | `N ngày` (đỏ ≤ 1, vàng ≤ 7, xám > 7) |
| Mã máy | 2 nhóm 5 + nút Sao chép |
| Nút | `Nhập mã mới` (mở ActivationDialog), `Đóng` |

### 9.3 Badge trên header (`ui/components/topbar.py`)

`🔑 Còn 23 ngày` · `🔑 Vĩnh viễn` · `🕐 Dùng thử: còn 5 ngày` · `⛔ Đã hết hạn` · `⚠ Máy không khớp`
Màu: xám (bình thường) · vàng (≤ 7 ngày) · đỏ (≤ 1 ngày / hết hạn / bị chặn). Cập nhật trong `_tick`.

---

## 10. Tool cấp mã (máy owner)

### 10.1 Sinh secret (P0, một lần)

`tools/license_tool/gen_secret.py`:

- `os.urandom(32)` → ghi `tools/license_tool/keys/license_secret.bin` (gitignored).
- In ra 4 mảnh hex để đối chiếu, nhắc backup ngay.
- Từ chối ghi đè nếu file đã tồn tại (tránh vô tình đổi secret).

### 10.2 `tools/license_tool/keygen.pyw` (GUI Tkinter)

| Trường | Ghi chú |
|---|---|
| Mã máy | Dán 10 ký tự; tự chuẩn hoá, hiện lại 2 nhóm 5 để kiểm tra |
| Loại | Radio: 7 ngày · 30 ngày · Vĩnh viễn · Tuỳ chỉnh (ô số ngày 1–3650) |
| Tên khách / SĐT / Ghi chú | Lưu vào sổ |
| Nút | `Tạo mã` · `Sao chép` · `Lưu .lic…` · `Ghi vào sổ` |
| Kết quả | Mã 15 ký tự (3 nhóm 5) + dòng "Hạn: dd/mm/yyyy" hoặc "Vĩnh viễn" |

Không cần mạng, chạy bằng python của venv.

### 10.3 Sổ key `issued.sqlite`

```sql
CREATE TABLE issued (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL,            -- mã 15 ký tự
  machine TEXT NOT NULL,         -- mã máy 10 ký tự
  kind INTEGER NOT NULL,
  days INTEGER NOT NULL,         -- 0 với vĩnh viễn
  issued_day INTEGER NOT NULL,   -- số ngày từ 01/01/2026
  expiry_day INTEGER,            -- NULL = vĩnh viễn
  customer TEXT, phone TEXT, note TEXT,
  created_at INTEGER NOT NULL,
  reissued_from INTEGER          -- id của mã cũ nếu cấp lại
);
CREATE INDEX idx_issued_machine ON issued(machine);
```

Dùng để: tra khách đã cấp mã nào, cấp lại khi đổi ổ/cài lại Windows, thống kê.
**Không** có chức năng thu hồi (offline không thu hồi được).

### 10.4 Quy trình cấp mã

1. Khách mở app → bấm "Sao chép" mã máy (10 ký tự) → gửi qua Zalo/điện thoại.
2. Owner mở `keygen.pyw` → dán mã máy → chọn loại → `Tạo mã`.
3. Gửi mã 15 ký tự (hoặc file `<MÃ>.lic`).
4. Khách dán vào app → `Kích hoạt`.
5. Bấm `Ghi vào sổ`.

**Chính sách cấp lại** (ghi trong `docs/HUONG_DAN_CAP_KEY.md`):
- Đổi/thay ổ cứng, format ổ, cài lại Windows → mã mới **miễn phí**, tra sổ theo tên/SĐT.
- Thay CPU **hoặc** mainboard → không cần cấp lại (hệ thống tự cập nhật `fp4`).
- Thay **cả** CPU và mainboard → hệ thống coi là clone, cấp lại sau khi xác minh khách.
- Không cấp lại mã cho máy thứ hai (mỗi mã 1 máy).

### 10.5 `tools/license_tool/license_cli.py`

Dùng khi cấp hàng loạt hoặc test tự động:

```
python license_cli.py --machine 7K2QF-9M3XA --kind 30
python license_cli.py --machine 7K2QF-9M3XA --kind custom --days 90
python license_cli.py --machine 7K2QF-9M3XA --kind lifetime
```

---

## 11. Build & cập nhật

### 11.1 Pipeline (`build_v3.bat`)

```
0) git status sạch · pytest · quét git history không chứa secret
1) robocopy source → build\src   (bỏ .venv, dist, build, tests, __pycache__)
2) python tools\inject_secret.py build\src     (ghi _k1..4 từ keys\license_secret.bin)
3) python tools\check_code_size.py build\src   (dừng nếu file > 30 KB)
4) pyarmor gen -O build\obf -r build\src
5) python -m PyInstaller --clean --noconfirm app_v3_modular.spec
6) robocopy build\obf dist\<APP> /E            (code đã obfuscate)
7) copy pyarmor_runtime_000000, docs, HDSD, logo
8) robocopy models …                            (chỉ lần build full)
9) python tools\make_manifest.py --dist dist\<APP>
10) python tools\make_update_zip.py --dist dist\<APP> --prev build\manifests\<ver_truoc>.json --out build\update_<ver>.zip
11) quét dist: không có *.key, *.lic, license_secret*, issued.sqlite, __pycache__, *.py chưa obfuscate
12) xoá build\src (chứa secret dạng plaintext)
```

`app_v3_modular.spec` (dựa trên `app_v2.spec`):

- `Analysis(['main.py'], excludes=['core','engine','audio','ui','version','tests','docs'])`
- `runtime_hooks=['hooks/rthook_v3_syspath.py']`
- `datas`: logo + metadata cần bundle trong `_internal`
- `console=False`, tên/icon như bản cũ

`hooks/rthook_v3_syspath.py`: chép logic `hooks/rthook_v2_syspath.py` (thêm thư mục exe vào đầu `sys.path`).

### 11.2 `manifest.json`

```json
{
  "app": "PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3",
  "version": "3.3.0",
  "python": "3.13",
  "pyarmor": "9.2.8",
  "key_format": 1,
  "built_at": "2026-10-27T09:00:00Z",
  "files": {
    "core/tags.py":       {"sha256": "…", "size": 12345},
    "ui/main_window.py":  {"sha256": "…", "size": 23456}
  }
}
```

Chỉ liệt kê file thuộc gói cập nhật được (code, docs, config); bỏ `models/`, `_internal/`, exe.

### 11.3 Gói cập nhật + `capnhat.bat`

```
update_3.3.1.zip
└─ capnhat_3.3.1\
    ├─ payload\                 # file đã đổi (+ runtime, + exe nếu exe đổi)
    │   ├─ ui\main_window.py
    │   ├─ pyarmor_runtime_000000\…
    │   └─ …
    ├─ manifest_update.json     # manifest của bản mới
    ├─ delete.txt               # file cần xoá (nếu có)
    ├─ capnhat.bat
    └─ capnhat.ps1
```

Kích thước thực tế đã đo: **0,25 MB** khi chỉ đổi code; **~29 MB** khi file `.exe`
cũng đổi (PyInstaller không tái lập byte-for-byte) — vẫn nhỏ hơn nhiều so với
gửi cả bộ cài ~1 GB.

`capnhat.bat` → `powershell -ExecutionPolicy Bypass -File capnhat.ps1`:

1. Xác định thư mục app (cạnh gói, hoặc chọn bằng hộp thoại).
2. Kiểm tra app không chạy; nếu đang chạy thì nhắc đóng.
3. So `version` giữa `manifest.json` của app và `manifest_update.json`.
4. Backup file sắp ghi đè **và** file sắp xoá vào `backup\<ver_cu>_<yyyymmdd_HHmmss>\`.
5. Copy `payload\*` đè lên thư mục app; xoá file trong `delete.txt`.
6. Tính `sha256` từng file vừa copy, so với manifest; sai → **rollback** toàn bộ và báo lỗi.
7. Ghi `manifest.json` mới, thông báo version, mở lại app.

Chỉ khi **Python hoặc PyArmor** thay đổi (nâng thư viện) mới cần build full.
Script hỗ trợ `-NoLaunch` và `-Quiet` để chạy tự động/kiểm thử.

### 11.4 Chặn lọt secret

- Bước 11 quét `dist/` và **dừng build** nếu thấy `*.key`, `*.lic`, `license_secret*`, `issued.sqlite`, `keys\`.
- Bước 0 chạy `git log --all --oneline -- '*secret*' '*.key' '*.lic'` — phải rỗng.
- `make_update_zip.py` chỉ nhận file trong danh sách trắng: `core/ engine/ audio/ ui/ version.py docs/ *.txt` + `pyarmor_runtime_000000`.
- `build/src` bị xoá sau build và nằm trong `.gitignore`.

---

## 12. Kiểm thử

### 12.1 `tests/test_shortcode.py` (~22 case)

| Nhóm | Case |
|---|---|
| Codec | base32 Crockford round-trip · encode/decode 75 bit · mã 14/16 ký tự bị từ chối · ký tự ngoài bảng chữ |
| Chuẩn hoá | có/không dấu gạch · chữ thường · `O→0` · `I→1` · `L→1` · `U→V` · khoảng trắng |
| Tag | mã đúng verify OK · sửa 1 ký tự → fail · sửa 1 bit → fail · tag so sánh constant-time |
| Trường | `ver != 1` → fail · đủ 4 kind · `kind=2` bỏ qua expiry · `expiry` biên 0 / 4095 |
| Máy | đúng `machine24` → OK · sai 1 bit → `machine_mismatch` |
| Hạn | hết hạn hôm qua → `expired` · hạn hôm nay → OK · vĩnh viễn luôn OK |

### 12.2 `tests/test_license.py` (~16 case)

| Nhóm | Case |
|---|---|
| Mã máy | 10 ký tự round-trip · đọc Guid + Volume · lỗi đọc → `UNKNOWN` · chuẩn hoá hiển thị 2 nhóm 5 |
| Clone | `fp4` đủ 4 thành phần · đổi 1 thành phần → cập nhật `fp4` · đổi CPU + mainboard → `clone_detected` · đổi Guid/Volume → `machine_mismatch` |
| Store | ghi/đọc `license.json` · JSON hỏng → `tampered` · sửa `max_seen` → `tampered` · không có quyền ghi → không crash |
| Đồng hồ | lùi 2 ngày OK · lùi 4 ngày → `clock_rollback` · `max_seen` lấy max 3 nơi |
| Rate limit | 10 lần sai → khoá 60 s · hết 5 phút reset · đúng mã trong lúc khoá → `rate_limited` |
| Trial | bắt đầu · hết 7 ngày · heuristic `app_settings.json` · `trial_start` lấy min 3 nơi |
| Secret | 4 mảnh ghép ra K ổn định · placeholder ≠ secret thật |

### 12.3 Probe

`packaging/probe_license.py` — chạy app thật:

1. Xoá license + `.state` + registry → ActivationDialog hiện mã máy 10 ký tự.
2. Bấm "Dùng thử" → badge "Dùng thử: còn 7 ngày".
3. Dán mã đúng → kích hoạt, badge đúng số ngày.
4. Dán mã của máy khác → "Mã này được cấp cho máy khác".
5. Sửa `license.json` → `tampered`, khoá xuất file (vẫn chuyển đổi được).
6. Giả `fp4` (CPU + mainboard khác) → `clone_detected`.
7. Lùi `max_seen` 5 ngày → `clock_rollback`.
8. Nhập sai 11 lần → khoá 60 giây, đếm ngược hiển thị.

`packaging/probe_obfuscated_build.py` — chạy exe trong `dist/`:

1. Không còn source `.py` đọc được.
2. Import từ đĩa chạy đúng; convert 1 câu + xuất MP3 + lịch sử OK.
3. `manifest.json` khớp sha256 toàn bộ file.
4. Không có secret/`*.lic`/`*.key` trong `dist/`.
5. Giải nén `update_*.zip` vào bản copy → chạy `capnhat.ps1` → app chạy, license còn nguyên.

### 12.4 Hồi quy

| Bộ | Yêu cầu |
|---|---|
| `pytest` | 83 test cũ + ~38 test mới, tất cả pass |
| `probe_menu_toolbar.py` | Kích thước/trạng thái không đổi so với 3.2.0 |
| `probe_tags_history.py` | Thẻ cảm xúc/nghỉ + lịch sử vẫn đúng |
| `probe_ui_flow.py` | Luồng chuyển đổi + xuất file vẫn đúng |

---

## 13. Lộ trình triển khai

| Phase | Công việc | File chính | Điều kiện xong | Ước lượng |
|---|---|---|---|---|
| **P0** | Tách 2 file lớn; cài PyArmor free; tạo `_k1..4` placeholder + `inject_secret.py`; sinh `license_secret.bin`; dựng `app_v3_modular.spec` + rthook; build thử 1 bản | `ui/window/*`, `merge_widgets.py`, `app_v3_modular.spec`, `hooks/rthook_v3_syspath.py`, `tools/inject_secret.py`, `tools/license_tool/gen_secret.py` | pytest 83 + 3 probe pass; exe modular chạy với code obfuscate; secret đã backup | 1 ngày |
| **P1** | `core/licensing/` + test | `fingerprint.py`, `shortcode.py`, `secret.py`, `store.py`, `trial.py`, `guard.py`, `tests/test_shortcode.py`, `tests/test_license.py` | ~38 test pass, không phụ thuộc GUI | 1 ngày |
| **P2** | UI + freemium gate (Xuất file/Ghép nhạc) + badge + menu | `activation_dialog.py`, `license_dialog.py`, `topbar.py`, `main_window.py`, `ui/window/*` | `probe_license.py` pass 14 bước | 1 ngày |
| **P3** | Tool cấp mã + sổ key + tài liệu owner | `keygen.pyw`, `license_cli.py`, `ledger.py`, `docs/HUONG_DAN_CAP_KEY.md` | Tạo mã từ mã máy thật, kích hoạt được | 0,5 ngày |
| **P4** | Build pipeline + manifest + gói update | `build_v3.bat`, `tools/make_manifest.py`, `tools/make_update_zip.py`, `tools/update_script/*`, `.gitignore` | Sinh `update_*.zip` < 3 MB; cài thử trên bản copy chạy đúng | 1 ngày |
| **P5** | Probe build obfuscate + hồi quy + docs + bump | `probe_obfuscated_build.py`, `version.py`, `README.md`, `plan_update.md` | Toàn bộ test/probe pass; 3.3.0; commit + push | 0,5–1 ngày |

Tổng: **~5 ngày**.

### Danh sách file sẽ thêm/sửa

**Thêm mới**

```
core/licensing/{__init__,fingerprint,shortcode,secret,store,trial,guard}.py
core/licensing/{_k1,_k2,_k3,_k4}.py            # placeholder, giá trị thật chỉ khi build
ui/components/activation_dialog.py
ui/components/license_dialog.py
ui/window/{__init__,convert,export,tools}.py
ui/components/merge_widgets.py
tools/license_tool/{gen_secret.py,keygen.pyw,license_cli.py,ledger.py}
tools/{inject_secret.py,make_manifest.py,make_update_zip.py,check_code_size.py}
tools/update_script/{capnhat.bat,capnhat.ps1}
app_v3_modular.spec
hooks/rthook_v3_syspath.py
packaging/{probe_license.py,probe_obfuscated_build.py}
tests/{test_shortcode.py,test_license.py}
docs/HUONG_DAN_CAP_KEY.md
plan_baomat.md                                  # tài liệu này
```

**Sửa**

```
main.py                  # mở app trực tiếp (freemium); gate nằm trong MainWindow
ui/main_window.py        # tách mixin + first-run prompt + badge + khoá xuất file
ui/components/topbar.py  # badge trạng thái bản quyền
build_v3.bat             # inject secret, PyArmor, manifest, update zip, quét bảo mật
version.py               # 3.3.0
.gitignore               # keys/, license_secret*, *.lic, issued.sqlite, build/src/
README.md                # mục bản quyền + build modular
plan_update.md           # mục 11: nhật ký triển khai
```

**Không dùng nữa** (đã bỏ khi chuyển sang mã 15 ký tự): `ed25519.py`, `public_key.py`, `gen_keypair.py`, `crypto.py`, file `.key` bất đối xứng.

---

## 14. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Reverse app → trích secret → keygen | Trung bình | Repo private, secret chia 4 mảnh, `__assert_armored__`; đã chấp nhận vì chọn mã ngắn |
| Mất secret | Cao | Backup 2 nơi ngay sau P0; keygen từ chối ghi đè |
| PyArmor free chặn file > 32 KB | Cao (đã xảy ra) | Tách 2 file ở P0; `check_code_size.py` dừng build |
| Obfuscate làm vỡ import/tkinter | Trung bình | Thử trên 1 module ở P0; `probe_obfuscated_build.py` |
| Người dùng patch bỏ kiểm tra | Trung bình | Các điểm chặn (xuất file / ghép nhạc) + kiểm tra chéo module |
| Đổi ổ/cài lại Windows phải cấp lại | Trung bình | Chính sách cấp lại miễn phí + sổ key |
| Clone ổ đĩa | Thấp | `fp4` 4 thành phần, chặn khi cả CPU + mainboard khác |
| Đồng hồ bị chỉnh | Trung bình | `max_seen` 3 nơi + ngưỡng 3 ngày |
| Khách cũ nâng cấp bị chặn | Trung bình | Cấp mã trước khi phát hành 3.3.0 |
| Runtime PyArmor gắn Python 3.13 | Trung bình | Ghim phiên bản, ship runtime trong mọi gói update |
| SmartScreen / antivirus | Thấp | Ghi chú trong HDSD; theo dõi phản hồi |
| Traceback mất số dòng | Thấp | Giữ build dev không obfuscate để debug |

---

## 15. Checklist trước khi phát hành 3.3.0

- [ ] `pytest` pass (83 cũ + ~38 mới)
- [ ] 4 probe pass (`menu_toolbar`, `tags_history`, `ui_flow`, `license`)
- [ ] `probe_obfuscated_build` pass trên `dist/`
- [ ] Không còn `.py` source gốc trong `dist/` (chỉ bản obfuscate)
- [ ] Không có `license_secret*`, `*.key`, `*.lic`, `issued.sqlite`, `keys\` trong `dist/`
- [ ] `git log --all` không chứa secret
- [ ] `manifest.json` khớp sha256 từng file
- [ ] `update_*.zip` cài thử trên bản copy → app chạy, license còn nguyên
- [ ] Mã 7 ngày / 30 ngày / vĩnh viễn / tuỳ chỉnh đều kích hoạt được, badge đúng
- [ ] Mã của máy khác bị chặn; sửa `license.json` bị chặn; lùi giờ 4 ngày bị chặn
- [ ] Clone giả lập (đổi CPU + mainboard) bị `clone_detected`
- [ ] Nhập sai 11 lần → khoá 60 giây
- [ ] Trial 7 ngày chạy đúng, hết hạn khoá Xuất file + Ghép nhạc (vẫn chuyển đổi được)
- [ ] `version.py` = 3.3.0
- [ ] `README.md`, `plan_update.md`, `docs/HUONG_DAN_CAP_KEY.md` cập nhật
- [ ] Secret đã backup 2 nơi
- [ ] Commit + push `origin/main`

---

## 16. Việc owner cần chuẩn bị

| # | Việc | Khi nào |
|---|---|---|
| 1 | Sinh `license_secret.bin` (P0) và **backup 2 nơi** | P0 |
| 2 | Cấp mã cho khách cũ trước khi phát hành 3.3.0 (họ không được trial) | Trước P5 |
| 3 | Ghi nhớ chính sách cấp lại: đổi ổ/cài lại Windows → miễn phí; thay cả CPU + mainboard → xác minh rồi cấp | Trước P5 |
| 4 | Kênh nhận mã máy (Zalo/email) — chỉ ghi trong tài liệu nội bộ, không hiện trong app | Trước P5 |
| 5 | Kiểm tra repo vẫn private sau mỗi lần đổi quyền/tổ chức | Định kỳ |

**Không còn điểm treo nào.** Toàn bộ quyết định (mã 15 ký tự, mã máy 10 ký tự, chống clone, dùng thử 7 ngày,
chống lùi giờ 3 ngày, freemium (chỉ khoá Xuất file + Ghép nhạc), build modular + PyArmor, gói update nhỏ, repo private) đã chốt.
Việc triển khai bắt đầu từ **P0** khi chuyển sang Build agent.


