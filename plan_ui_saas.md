# KẾ HOẠCH — CHUYỂN UI SANG MÔ HÌNH SAAS (`v3.5.0`)

> **Trạng thái:** kế hoạch, **chưa triển khai**.
> **Mốc hiện tại:** `v3.4.0` (menu bar + header 3 hàng + 9 dialog rời).
> **Bản đích:** `v3.5.0` — **gộp toàn bộ** thay đổi UI + hội thoại nhiều giọng vào một bản.
> **Không phát hành trung gian** (`3.6.0` bỏ). `4.0.0` để dành cho đợt sau khi có nhu cầu.
> **Ngày lập:** 01/11/2026
> **Tài liệu liên quan:** `plan_dialogue.md` (đã cập nhật theo shell mới), `plan_update.md`.

---

## 0. Quyết định đã chốt

| # | Nội dung | Quyết định |
|---|---|---|
| 1 | Mục sidebar | 5 mục chính: **Đọc văn bản, Hội thoại, Ghép nhạc, Hàng loạt, Lịch sử**; 4 mục Công cụ: **Từ điển, Giọng đọc, Cài đặt, Bản quyền** |
| 2 | Player | **Dùng chung** một thanh phát ở đáy cho mọi trang |
| 3 | Waveform | **Đưa vào thanh chung** (waveform + seek + transport + tốc độ) |
| 4 | Phạm vi phát hành | **Toàn bộ trong `v3.5.0`**, không phát hành `3.6.0` |
| 5 | Sidebar thu gọn | **Có** — 232 px ↔ 64 px (icon + tooltip) |
| 6 | Màu sắc | **Đổi sang palette SaaS mới** (trắng/xám + xanh dương) |
| 7 | Modal | Chỉ giữ modal cho **Kích hoạt**, **Điều khoản**, **Tạo/Nhập giọng**; còn lại thành page |

---

## 1. Mục tiêu

- Giao diện **liền mạch**: header + toolbar + sidebar + vùng nội dung, không mở dialog rời cho các chức năng chính.
- Mỗi chức năng là **một page** có tiêu đề, mô tả, nút hành động riêng; chuyển qua lại **không mất trạng thái**.
- Dùng chung **một thanh phát** (waveform + seek + tốc độ) cho mọi trang tạo audio.
- Hệ thống thiết kế thống nhất: màu, khoảng cách, nút, card, bảng, form.
- Giữ nguyên toàn bộ **logic nghiệp vụ** (core/engine/audio) và phím tắt hiện có.

**Ngoài phạm vi:** dark mode, đa ngôn ngữ UI, đa nền tảng, thay đổi engine TTS.

---

## 2. Bố cục chuẩn

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [logo] Phần mềm chuyển đổi văn bản thành giọng nói             v3.5.0       │ 56
├──────────────────────────────────────────────────────────────────────────────┤
│  Tệp ▾    Trợ giúp ▾                              ● Sẵn sàng · 26/26 giọng   │ 40
├───────────────┬──────────────────────────────────────────────────────────────┤
│ 📖 Đọc văn bản│  Page header: tiêu đề + mô tả                 [phụ] [chính]  │
│ 🎭 Hội thoại  │  ──────────────────────────────────────────────────────────  │
│ 🎵 Ghép nhạc  │                                                              │
│ 📦 Hàng loạt  │  Nội dung trang (card, form, bảng, editor…)                  │
│ 🕘 Lịch sử    │                                                              │
│               │                                                              │
│ ─ Công cụ ─   │                                                              │
│ 📖 Từ điển    │                                                              │
│ 🎙 Giọng đọc  │                                                              │
│ ⚙ Cài đặt     │                                                              │
│ 🔑 Bản quyền  │                                                              │
│               │                                                              │
│ ───────────── │                                                              │
│ 🔑 Còn 23 ngày│                                                              │
├───────────────┴──────────────────────────────────────────────────────────────┤
│  ⏮  ▶  ⏭   ┌──── waveform + vùng đã phát ────┐  01:12 / 03:45   1.0x ▾     │ 112
│  −5s +5s    └─────────────────────────────────┘                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Vùng | Chiều cao | Nội dung |
|---|---|---|
| Header | 56 | logo 32 px + tên app + chip `v3.5.0` |
| Toolbar | 40 | menu `Tệp`, `Trợ giúp`; bên phải: chấm trạng thái + “Sẵn sàng · 26/26 giọng” |
| Sidebar | 232 (thu gọn 64) | 5 mục chính, 4 mục công cụ, chân: trạng thái bản quyền |
| Content | co giãn | `PageHeader` + nội dung cuộn |
| PlayerBar | 112 (ẩn khi chưa có audio) | waveform + seek + ⏮ ▶ ⏭ + −5/+5 + thời lượng + tốc độ |

App min size: **1024×640**; mặc định **1280×800**.

---

## 3. Palette SaaS

Ghi đè `ui/theme.py` (giữ tên token cũ để code đang dùng không vỡ, thêm token mới).

| Token | Mã | Dùng cho |
|---|---|---|
| `BG` | `#F6F7F9` | nền app |
| `SURFACE` | `#FFFFFF` | card, sidebar, toolbar, player |
| `SURFACE_2` | `#F9FAFB` | input, hover nhẹ |
| `BORDER` | `#E5E7EB` | viền card/input/sidebar |
| `TEXT` | `#111827` | chữ chính |
| `TEXT_DIM` | `#6B7280` | mô tả, nhãn |
| `PRIMARY` | `#2563EB` | nút chính, mục sidebar active |
| `PRIMARY_HOVER` | `#1D4ED8` | hover |
| `PRIMARY_SOFT` | `#EFF6FF` | nền mục active, badge |
| `SUCCESS` | `#16A34A` | trạng thái xong |
| `SUCCESS_SOFT` | `#DCFCE7` | nền badge |
| `DANGER` | `#DC2626` | lỗi, nút xoá |
| `DANGER_SOFT` | `#FEE2E2` | nền cảnh báo đỏ |
| `WARNING` | `#D97706` | cảnh báo |
| `WARNING_SOFT` | `#FEF3C7` | nền cảnh báo vàng |
| `WAVE_DIM` | `#DBEAFE` | waveform chưa phát |
| `WAVE_PLAYED` | `#2563EB` | waveform đã phát |

Chữ: Segoe UI, scale **11 / 12 / 13 / 15 / 18 / 22**. Bo góc **8 / 10 / 14**. Khoảng cách **4 / 8 / 12 / 16 / 24 / 32**.
Chỉ **light mode** ở 3.5.0.

---

## 4. Design system (`ui/ui_kit.py`)

Mọi page **chỉ dùng** các thành phần dưới đây, không tự khai báo màu/kích thước nút.

| Thành phần | API dự kiến |
|---|---|
| `Button` | `Button(parent, text, variant="primary"\|"secondary"\|"ghost"\|"danger"\|"icon", size="sm"\|"md", command=…)` |
| `Card` | `Card(parent)` — nền trắng, viền, radius 14, padding 16–20 |
| `PageHeader` | `PageHeader(parent, title, subtitle, actions=[widget…])` |
| `SectionTitle` | `SectionTitle(parent, title, hint=None)` |
| `Field` | `Field(parent, label, widget, hint=None, error=None)` |
| `Table` | `Table(parent, columns=[(key,label,width,anchor)], rows, on_row_click=None)` |
| `EmptyState` | `EmptyState(parent, icon, title, hint, action=None)` |
| `Switch`, `Segmented` | công tắc, chọn chế độ |
| `Badge` | trạng thái (xanh/vàng/đỏ/xám) |
| `DialogShell` | modal thống nhất: header + body + footer nút |
| `Tooltip` | nhãn khi sidebar thu gọn |

Kích thước chuẩn: nút **36** (md) / **32** (sm) / **40** (primary page), input **36**, hàng bảng **40**, icon sidebar **20**.

---

## 5. Shell, router, context

```
MainWindow
└─ AppShell
   ├─ AppHeader
   ├─ AppToolbar
   ├─ NavSidebar (thu gọn được)
   ├─ Router (content)
   └─ PlayerBar (waveform + transport + speed)
```

### 5.1. `Page` base

```python
class Page(ctk.CTkFrame):
    id: str
    label: str
    icon: str

    def on_show(self) -> None: ...      # nạp dữ liệu, focus, refresh
    def on_hide(self) -> None: ...      # dừng preview riêng, lưu nháp
    def set_busy(self, busy: bool) -> None: ...
```

- Router **cache** page (tạo lazy lần đầu), chuyển trang: `on_hide()` → ẩn → `on_show()`.
- `AppShell.show(page_id)` công khai; sidebar và phím `Ctrl+1…9` gọi hàm này.

### 5.2. `AppContext` (service dùng chung)

| Trường | Vai trò |
|---|---|
| `settings` | cấu hình chung (precision/threads/storage) |
| `model_manager` | nạp/giải phóng model |
| `history` | `HistoryStore` |
| `player` | `AudioPlayer` dùng chung |
| `license` | `guard`/`trial`/`store` |
| `status(text, level)` | cập nhật thanh trạng thái toolbar |
| `navigate(page_id, payload=None)` | chuyển trang (vd. Lịch sử → Ghép nhạc) |

### 5.3. `AudioSession`

Mỗi trang tạo audio sở hữu một phiên:

```
base_store, play_store, base_timeline, timeline, base_spans,
applied_speed, speed_dirty, disk_mode, temp_session, store_seq,
current_sentence, synth_text
```

- PlayerBar gắn với phiên của trang đang mở.
- Chuyển trang: dừng phát, giữ nguyên phiên (quay lại vẫn còn audio/timeline).
- Page không có audio (Cài đặt, Từ điển…) → PlayerBar ẩn.

### 5.4. Trạng thái bận

- `ctx.set_busy(True)`: khoá sidebar (trừ Lịch sử), toolbar, nút hành động các page; nút chính đổi `⏹ Dừng`.
- Không cho chuyển trang khi đang tổng hợp (tránh worker ghi vào page khác).

---

## 6. Danh sách trang

| Page | Nội dung | Nguồn port |
|---|---|---|
| **Đọc văn bản** | Page header (Mở file, Chuyển đổi, Xuất file) + TagBar + editor + card trạng thái | `TopBar` + vùng soạn thảo hiện tại |
| **Hội thoại** | Editor kịch bản + cột phải “Nhân vật & giọng” (combobox, nghe thử, gán tự động, số lượt) + danh sách lỗi theo dòng | `plan_dialogue.md` |
| **Ghép nhạc** | Track intro/nền/outro, timeline 3 màu, preview, xuất | `merge_dialog.py` + `merge_widgets.py` |
| **Hàng loạt** | Editor `[P1]…`, bảng phần (bật/tắt, số câu), chọn giọng/tốc độ, zip | `batch_dialog.py` |
| **Lịch sử** | Bảng bản dựng (thời gian, giọng, thời lượng, dung lượng), nghe, mở thư mục, xoá, “Mở trong Ghép nhạc” | `history_dialog.py` |
| **Từ điển** | Bảng mục + form thêm/sửa + tìm kiếm + nhập/xuất | `dictionary_dialog.py` |
| **Giọng đọc** | Checklist giọng, bảng giọng tùy chỉnh (xuất/xoá), nút nhập/tạo (modal) | `voice_manager.py` |
| **Cài đặt** | Precision, threads, chế độ lưu + Lưu; cảnh báo khi rời trang chưa lưu | `settings_dialog.py` |
| **Bản quyền** | Trạng thái, loại, hạn, còn lại, mã máy + sao chép, nhập mã mới | `license_dialog.py` |

**Modal giữ lại** (bọc `DialogShell`): Kích hoạt, Điều khoản, Tạo/Nhập giọng.

---

## 7. Menu, phím tắt, sidebar

### 7.1. Toolbar

| Menu | Mục |
|---|---|
| **Tệp** | Mở văn bản… (`Ctrl+O`), Mở thư mục dữ liệu, Thoát (`Alt+F4`) |
| **Trợ giúp** | Hướng dẫn sử dụng, Điều khoản sử dụng, Thông tin bản quyền (`Ctrl+Shift+L`), Giới thiệu |

Bỏ menu **Công cụ** (đã thành sidebar). Bên phải toolbar: chấm trạng thái + text + số giọng.

### 7.2. Phím tắt

| Phím | Hành động |
|---|---|
| `Ctrl+1…9` | Chuyển page theo thứ tự sidebar |
| `Ctrl+O` | Mở văn bản |
| `Ctrl+H` | Lịch sử |
| `Ctrl+B` | Hàng loạt |
| `Ctrl+Shift+D` | Từ điển |
| `Ctrl+Shift+L` | Bản quyền |
| `Ctrl+Shift+K` | Làm sạch văn bản (trong page Đọc văn bản) |
| `Ctrl+Shift+S` | Ghép nhạc (mới) |
| `Alt+F` / `Alt+T` | Mở menu Tệp / Trợ giúp |

### 7.3. Sidebar

- Mục active: nền `PRIMARY_SOFT`, chữ `PRIMARY`, vạch 3 px bên trái.
- Thu gọn 64 px: chỉ icon, tooltip hiện tên; nút `«` ở đáy để chuyển.
- Chân sidebar: badge bản quyền (`🔑 Còn N ngày` / `Vĩnh viễn` / `Dùng thử` / `⛔ Hết hạn`), bấm → page Bản quyền.

---

## 8. File & ước lượng

### 8.1. Mới

```
ui/shell/__init__.py
ui/shell/app_shell.py        # layout + router + tick               ~8 KB
ui/shell/app_header.py       # logo + tên + version                 ~3 KB
ui/shell/app_toolbar.py      # menu Tệp/Trợ giúp + trạng thái       ~6 KB
ui/shell/nav_sidebar.py      # sidebar + thu gọn + badge            ~8 KB
ui/shell/page.py             # Page base + PageHeader               ~4 KB
ui/shell/player_bar.py       # waveform + transport + speed         ~9 KB
ui/ui_kit.py                 # design system                        ~13 KB
ui/pages/__init__.py
ui/pages/text_page.py        ~12 KB
ui/pages/dialogue_page.py    ~16 KB   (sau core/engine hội thoại)
ui/pages/merge_page.py       ~16 KB
ui/pages/batch_page.py       ~15 KB
ui/pages/history_page.py     ~10 KB
ui/pages/dictionary_page.py  ~15 KB
ui/pages/voices_page.py      ~16 KB
ui/pages/settings_page.py    ~10 KB
ui/pages/license_page.py     ~8 KB
ui/components/dialog_shell.py ~6 KB
packaging/probe_shell.py
packaging/probe_navigation.py
packaging/probe_pages.py
```

### 8.2. Sửa

| File | Thay đổi |
|---|---|
| `ui/main_window.py` | Chỉ khởi tạo shell + service + tick; bỏ layout cũ |
| `ui/theme.py` | Palette mới + token bổ sung |
| `ui/window/convert.py`, `export.py` | Tách thành `SessionController` dùng chung cho Text/Dialogue |
| `ui/window/tools.py`, `license_ui.py`, `messages.py` | Chuyển vào page/status toàn cục |
| `ui/components/tag_bar.py` | Giữ, chỉnh style theo ui_kit |
| `ui/components/waveform_timeline.py` | Nhúng vào `PlayerBar` |
| `ui/components/playback_bar.py` | Thay bằng transport trong `PlayerBar` |
| `engine/vieneu_engine.py` | `set_voice()` (cho hội thoại) |
| `core/text_processor.py` | `clean_for_reading` không gộp dòng `Tên:` |
| 7 probe cũ | Cập nhật theo shell mới |
| `version.py` | 3.5.0 |
| `docs/gen_hdsd_v3.py`, `README.md`, `plan_update.md`, `plan_dialogue.md` | Tài liệu |

### 8.3. Xoá sau khi port xong

`ui/components/topbar.py`, `sidebar.py`, `merge_dialog.py`, `batch_dialog.py`,
`history_dialog.py`, `settings_dialog.py`, `dictionary_dialog.py`,
`voice_manager.py`, `license_dialog.py`, `activation_dialog.py`, `terms_dialog.py`,
`voice_import_dialog.py` (thay bằng page/modal mới).

> Giữ **shim** `MainWindow.topbar/textbox/playback_bar/tag_bar` trong P0–P4 để probe cũ chạy; gỡ ở P5.

---

## 9. Luồng dữ liệu

```
Người dùng chọn mục sidebar
  → AppShell.show(page_id)
      → page cũ: on_hide()  (dừng preview riêng, lưu nháp)
      → page mới: on_show() (refresh dữ liệu, focus)
  → PlayerBar.bind(session của page nếu có)
  → Sidebar cập nhật active

Hành động trên page
  → ctx.set_busy(True) → khoá điều hướng + nút
  → worker (thread) → message queue → page xử lý
  → xong: ctx.set_busy(False), ctx.status("…", "success")
```

- Chuyển trang **không** dừng audio đang phát? Quyết định: **dừng** khi rời page có audio (tránh tiếng từ page ẩn), trạng thái phiên giữ nguyên để phát tiếp.
- Lịch sử → “Mở trong Ghép nhạc”: `navigate("merge", payload={"files": [...]})`.

---

## 10. Giai đoạn triển khai

| Phase | Nội dung | Điều kiện xong | Ước lượng |
|---|---|---|---|
| **P0** | Palette + `ui_kit` + shell (header/toolbar/sidebar/router/player) + `TextPage` | App dùng được như 3.4.0; chuyển trang giữ audio; sidebar thu gọn; header 56/sidebar 232 | 4 ngày |
| **P1** | SettingsPage, DictionaryPage, VoicesPage, LicensePage | 4 dialog cũ xoá; CRUD đầy đủ; lưu cấu hình | 4 ngày |
| **P2** | BatchPage, HistoryPage | Xuất hàng loạt + lịch sử chạy trong page | 3 ngày |
| **P3** | MergePage | Ghép nhạc + preview + xuất trong page | 4 ngày |
| **P4** | DialoguePage + `core/dialogue.py` + `engine/dialogue_engine.py` | 2 giọng, timeline, lỗi dòng thiếu tên, xuất, gate | 5 ngày |
| **P5** | `DialogShell` cho 3 modal + HDSD ảnh mới + build 3.5.0 | Toàn bộ probe pass; HDSD mới; `update_3.5.0.zip` | 3 ngày |

**Tổng ~23 ngày (~3,5 tuần).**

---

## 11. Kiểm thử

### 11.1. Unit test

- `pytest` hiện có (210) giữ nguyên (core/engine không đổi hành vi).
- Thêm ~10 test cho router/state (không cần GUI): `Page` lifecycle, cache, `AudioSession` chuyển phiên, `ui_kit` helper thuần (format, validate).
- ~25 test hội thoại (xem `plan_dialogue.md`).

### 11.2. Probe

| Probe | Nội dung |
|---|---|
| `probe_shell` (mới) | Header 56, toolbar 40, sidebar 232/64, player 112/ẩn; 4 bề rộng 1024/1200/1440/1600 |
| `probe_navigation` (mới) | Chuyển 9 trang, thời gian < 300 ms/trang; state không mất; busy khoá điều hướng; `Ctrl+1…9` |
| `probe_pages` (mới) | Mỗi page chạy hành động chính (lưu cài đặt, thêm từ điển, tick giọng, xuất hàng loạt, xoá lịch sử) |
| `probe_menu_toolbar` | Viết lại theo toolbar/header mới |
| `probe_tags_history` | Chạy trong TextPage |
| `probe_ui_flow` | 3 ca chuyển đổi/xuất trong TextPage |
| `probe_license` | Badge ở sidebar + page Bản quyền + modal kích hoạt |
| `probe_editor_tools` | Từ điển/làm sạch trong TextPage |
| `probe_batch` | BatchPage |
| `probe_terms` | Modal điều khoản (DialogShell) |
| `probe_dialogue` (mới) | Hội thoại 2 giọng + lỗi dòng thiếu tên + xuất |

### 11.3. Hồi quy

- `check_code_size`: mỗi file < 25 KB code object.
- Build `build_v3.bat test` → `probe_obfuscated_build`.
- Không tăng RAM đáng kể: page cache giữ widget, audio theo cơ chế cũ.

---

## 12. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Refactor vỏ làm vỡ luồng chuyển đổi/xuất | **Cao** | P0 giữ nguyên logic, chỉ đổi vỏ; shim thuộc tính; probe 2 chiều |
| Port `MergeDialog` (24,9 KB + preview player riêng) | **Cao** | Tách page + widgets; preview dùng PlayerBar chung; probe riêng |
| Sidebar 232 làm hẹp vùng làm việc @1024 | Trung bình | Thu gọn 64 px; kiểm tra 4 bề rộng; min size 1024×640 |
| Mất trạng thái khi chuyển trang | Trung bình | Router cache; `on_hide/on_show`; test chuyển 3 vòng |
| 32 KB PyArmor khi page phình | Trung bình | Chia page; `check_code_size` chặn build |
| HDSD 100% ảnh cũ | **Cao** | Sinh lại toàn bộ sau P5, 12–14 ảnh mới |
| Người dùng quen UI cũ | Trung bình | Giữ phím tắt; HDSD có mục “Giao diện mới”; bản 3.5.0 ghi rõ thay đổi |
| Modal kích hoạt/điều khoản bị lỗi khi đổi shell | Trung bình | `DialogShell` + probe_license/probe_terms |
| Trùng lặp style (page tự khai báo màu) | Trung bình | Review: chỉ dùng `ui_kit`; thêm checklist PR |

---

## 13. Định nghĩa hoàn thành (`v3.5.0`)

- [ ] Header 56 (logo + tên + version), toolbar 40 (Tệp/Trợ giúp), sidebar 232↔64
- [ ] 9 page hoạt động, chuyển trang không mất dữ liệu, phím `Ctrl+1…9`
- [ ] Player chung có waveform + seek + transport + tốc độ, ẩn khi không có audio
- [ ] 9 dialog cũ đã chuyển thành page/modal mới, không còn `grab_set` cho chức năng chính
- [ ] Hội thoại nhiều giọng chạy trong `DialoguePage` (theo `plan_dialogue.md`)
- [ ] Palette SaaS mới áp dụng toàn bộ; không còn màu theme cũ
- [ ] `pytest` ~245 pass; 11 probe pass; `check_code_size` OK
- [ ] Build `3.5.0` + `update_3.4.0 → 3.5.0`; HDSD ảnh mới; README/plan cập nhật

---

## 14. Việc chưa làm ở 3.5.0

- Dark mode (theme tối) — cân nhắc `4.0.0`.
- Đa ngôn ngữ UI.
- Sidebar kéo thay đổi độ rộng bằng chuột (chỉ 2 mức 232/64).
- “Mở/Lưu .txt” cho kịch bản hội thoại (đang chỉ dán text).
- `infer_batch` cho hội thoại (chờ GPU).
- Đa nền tảng Linux/macOS (đã bỏ khỏi scope).

---

## 15. Ghi chú ảnh hưởng tới `plan_dialogue.md`

- Bỏ phương án “tab Văn bản / Hội thoại” và “header đổi theo tab”.
- Hội thoại trở thành **`DialoguePage`** trong shell mới: page header + editor + cột phải “Nhân vật & giọng”.
- Phần `core/dialogue.py` và `engine/dialogue_engine.py` giữ nguyên thiết kế.
- P0 của kế hoạch hội thoại (tách menubar/header stack) **không còn** — đã nằm trong P0 của kế hoạch UI.
- Tổng thời gian hội thoại rút còn ~4 ngày (P4 của kế hoạch UI).

---

## 16. Thứ tự thực hiện khi bắt đầu

1. Tạo `plan_ui_saas.md` (tài liệu này) + cập nhật `plan_dialogue.md`.
2. **P0**: `ui/theme.py` palette mới → `ui/ui_kit.py` → `ui/shell/*` → `ui/pages/text_page.py` → chạy app + probe shell.
3. P1 → P2 → P3 → P4 → P5, mỗi phase chạy lại probe trước khi sang phase tiếp.
4. Build `v3.5.0`, sinh HDSD mới, tạo gói update, commit + push.

---

## 17. Nhật ký thực hiện

### P0 — xong (01/11/2026)

| Hạng mục | Kết quả |
|---|---|
| Palette SaaS | `ui/theme.py` đổi toàn bộ sang trắng/xám + xanh `#2563EB`; giữ tên token cũ nên code đang dùng không vỡ |
| Design system | `ui/ui_kit.py`: `Button`, `IconButton`, `Card`, `Badge`, `PageHeader`, `SectionTitle`, `Field`, `EmptyState`, `Table`, `Tooltip` |
| Shell | `ui/shell/`: `AppHeader` 56, `AppToolbar` 40 (Tệp/Trợ giúp), `NavSidebar` 232↔64, `PlayerBar` 108 (waveform + transport + tốc độ), `Page` base, `AppShell` router |
| TextPage | `ui/pages/text_page.py`: page header (Mở file / Xuất file / Chuyển đổi), hàng giọng đọc + test, TagBar, editor |
| Điều hướng | Sidebar 9 mục; `Ctrl+1…9`; chức năng chưa port mở dialog cũ; busy khoá điều hướng (trừ Lịch sử) |
| Tương thích | Alias `app.topbar`, `textbox`, `tag_bar`, `playback_bar`, `waveform_timeline` để mixin/probe cũ chạy |
| Player | Ẩn khi chưa có audio, hiện khi bắt đầu stream |
| Kiểm thử | `pytest` **210/210**; `probe_shell` **OK** (header/toolbar/sidebar/player, menu, phím tắt, busy, thu gọn, giữ trạng thái); `probe_license`, `probe_terms`, `probe_editor_tools`, `probe_tags_history`, `probe_ui_flow`, `probe_batch` **OK** |
| Kích thước | 1280×800: editor 434 px; 1024×700: editor 334 px; header 56 / toolbar 40 / sidebar 232 / player 108 |
| Dọn dẹp | Xoá `packaging/probe_menu_toolbar.py` (gộp vào `probe_shell.py`) |
| Còn lại của P0 | `probe_navigation` riêng (hiện nằm trong `probe_shell`) |

### P1 — xong (01/11/2026)

| Page | Nội dung | Ghi chú |
|---|---|---|
| `SettingsPage` | Precision / threads / lưu trữ; nút Lưu + badge “Chưa lưu”; cảnh báo INT8 | Lưu vào `app_settings.json`, nạp lại model khi đổi precision/threads |
| `LicensePage` | Badge trạng thái, loại, hạn, còn lại, mã máy + sao chép, nút nhập mã, hướng dẫn | `on_show` tự refresh; kích hoạt qua modal cũ |
| `DictionaryPage` | Form thêm/sửa, bảng + tìm kiếm, bật/tắt, nhập/xuất tệp | Lưu ngay; báo `_on_dictionary_changed` để vô hiệu audio cũ |
| `VoicesPage` | Checklist 26 giọng, chọn tất cả/bỏ chọn, lưu, nhập/tạo/xuất/xoá giọng | Tạo/nhập vẫn là modal `ImportVoiceDialog` |

- `probe_pages` **OK**: 4 page đăng ký, lưu cài đặt, thêm từ điển, lưu lựa chọn giọng, trang bản quyền, không mở dialog khi điều hướng.
- `probe_shell`, `probe_license`, `probe_terms`, `probe_editor_tools`, `probe_tags_history` **OK**; `pytest` **210/210**.
- Sửa lỗi layout: `Page.body` không còn tự đặt `row0 weight=1` (gây khoảng trống lớn ở đầu page).
- Bỏ vài glyph emoji không hiển thị trên Segoe UI (⬆⬇☑🔓💾) ở 4 page mới.

### P2 — xong (01/11/2026)

| Page | Nội dung | Ghi chú |
|---|---|---|
| `BatchPage` | Editor `[P1]…`, bảng phần, chọn tất cả/bỏ, tên tệp, thư mục, MP3/WAV, zip, tiến trình, huỷ | Tự lấy văn bản từ trang Đọc văn bản; gate bản quyền 2 lớp; dùng `TtsEngine` + `exporter` như cũ |
| `HistoryPage` | Danh sách bản dựng, nghe, mở thư mục, xoá từng bản / tất cả, cảnh báo 500 MB | Dùng player ngoài hệ thống như cũ |

- Kiểm chứng: BatchPage xuất thật 2 phần → 2 MP3 (`bai_P1.mp3`, `bai_P2.mp3`), status “Xong: 2 tệp…”.
- HistoryPage hiển thị đúng tổng dung lượng, empty state.
- `probe_shell`, `probe_pages`, `probe_license`, `probe_terms`, `probe_editor_tools`, `probe_tags_history` **OK**; `pytest` **210/210**.

### P2.5 — sửa padding + player luôn hiển thị (01/11/2026)

| Việc | Chi tiết |
|---|---|
| `Card` có vùng đệm | `ui_kit.Card` tạo `content` frame bên trong, `padx/pady = padding` (12/16 px) |
| Migrate 7 page | Text, Settings, License, Dictionary, Voices, Batch, History đặt widget vào `card.content` |
| Nút không sát viền | Hàng nút cuối (🗑/📂/⬇/…) cách mép ≥ 8 px; kiểm tra tự động trong `probe_pages` |
| Player luôn hiển thị | Bỏ ẩn/hiện; transport (⏮ −5 ▶ +5 ⏭ + tốc độ) **disable** khi chưa có audio, bật khi có source |
| Probe | `probe_shell` kiểm tra luôn hiển thị + disable/enable; `probe_pages` kiểm tra padding `<8 px` = 0 lỗi |

Kết quả: `pytest` **210/210**; `probe_shell`, `probe_pages`, `probe_editor_tools`, `probe_tags_history`, `probe_terms` **OK**.
Editor còn **310 px** @1024×700, **410 px** @1280×800.

### P2.6 — hiện toolbar + dàn cột Hàng loạt (01/11/2026)

| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| Toolbar không hiện | Đường phân cách trong `AppToolbar` là `CTkFrame` mặc định cao **200 px** → đẩy nút `Tệp/Trợ giúp` và trạng thái xuống ngoài vùng 40 px | Đặt `height=1`; thêm check mọi widget toolbar nằm trong biên 40 px (`probe_shell`) |
| Hàng loạt: trái hẹp, phải rộng vô ích | Cột phải đòi min-width ~600 px (2 entry cùng hàng) nên weight 3:2 vô hiệu | Hai cột `weight 3:2` + `uniform="batch"` (60/40); form tuỳ chọn xếp **dọc**, entry width 120 |

Kết quả đo: @1024 trái 434 / phải 298 (41%); @1280 588/400 (40%); @1440 684/464 (40%).
`probe_shell` OK (toolbar không còn widget bị cắt), `probe_pages` OK (padding 0 lỗi, cột đạt yêu cầu).

### P3 — xong (01/11/2026)

| Việc | Chi tiết |
|---|---|
| MergePage | ui/pages/merge_page.py — MergePage(MergeWidgetsMixin, Page), cuộn dọc, không còn Toplevel |
| merge_widgets.py | _build_ui(parent, history) dựng vào Page.body; bỏ nút/seek bar riêng (dùng player chung) |
| Player chung | PlayerBar.set_handlers() + set_speed_enabled(): trang Ghép nhạc điều khiển preview, khoá tốc độ; rời trang trả handler + khôi phục waveform cho TextPage |
| Header | Chọn file gốc · Nghe thử · Ghép & Xuất (primary) |
| Preview | AudioPlayer riêng + waveform trên PlayerBar chung; tick 40 ms khi trang đang mở |
| Xuất | Giữ mixer.merge, gate bản quyền 2 lớp, báo qua toolbar + status trong trang |
| Probe | probe_merge_page **OK**: thêm file gốc, preview (1 s), xuất MP3 5 KB, chuyển trang giữ file, tốc độ trả lại cho trang Văn bản |

pytest **212/212**; probe_shell, probe_pages, probe_merge_page, probe_tags_history, probe_license, probe_ui_flow **OK**.

### P4 — xong (01/11/2026)

| Việc | Chi tiết |
|---|---|
| `core/dialogue.py` | Parse `Tên: nội dung`, lỗi theo dòng, gộp tên trùng, offset ký tự; `dialogue_cast.json` (nhớ giọng), `dialogue_draft.txt` (nháp), kịch bản mẫu |
| `engine/dialogue_engine.py` | `render_dialogue`: đổi giọng theo lượt (`set_voice`, không nạp lại model), nghỉ giữa lượt, timeline quy về ký tự kịch bản, huỷ giữa chừng |
| `engine/vieneu_engine.py` | `set_voice()` (nhận cả `vieneu:...`) |
| `DialoguePage` | Editor + cột phải “Nhân vật & giọng”, gán tự động nam/nữ xen kẽ, 🔊 nghe thử, lỗi + “Sửa dòng N”, tạo/xuất, player chung |
| An toàn | Thiếu tên/nội dung → chặn tạo; đang tạo khoá sidebar (trừ Lịch sử); xuất cần bản quyền |
| Làm sạch | `clean_for_reading` không gộp dòng `Tên:` |
| Test | `tests/test_dialogue.py` **24 pass**; `probe_dialogue` **OK** (3 lượt, 4 câu, 6,3 s, MP3 54 KB) |

Tổng `pytest` lên **236 test**.

### P5 — xong (01/11/2026)

| Việc | Chi tiết |
|---|---|
| Dọn dialog cũ | Xoá 	opbar.py, playback_bar.py, sidebar.py, settings_dialog.py, dictionary_dialog.py, history_dialog.py, atch_dialog.py, merge_dialog.py, oice_manager.py, license_dialog.py, placeholder_page.py |
| Điều hướng | 	ools.py / license_ui.py chỉ còn shell.show(page); open_in_system chuyển vào core/paths.py |
| Probe | probe_batch chuyển sang BatchPage; probe_tags_history kiểm tra HistoryPage |
| HDSD | Sinh Huong_dan_su_dung_V3_v3.5.0.docx với chương 10 “Giao diện SaaS & Hội thoại”; build tự chọn HDSD mới nhất |
| Version | 3.5.0 |
| Build | uild_v3.bat test → 84 file / 32,7 MB; manifest 3.5.0; update_3.5.0.zip 29,96 MB (3.4.0 → 3.5.0, 81 file payload + 11 file xoá) |
| Kiểm tra | probe_obfuscated_build **OK** (sha256, obfuscate, không secret, exe mở cửa sổ) |

**Chưa làm trong P5:** DialogShell dùng chung cho 3 modal (Kích hoạt / Điều khoản / Tạo giọng) — giữ nguyên giao diện hiện tại, dời sang 4.0.0 cùng dark mode.

### P5.1 — sửa lỗi sau kiểm thử (01/11/2026)

| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| Waveform Hội thoại/Ghép nhạc trắng xoá, đứng im | `PlayerBar.set_position()` không cập nhật waveform; cột chưa phát hardcode `#e6eefb` gần trùng nền mới | `set_position` gọi `waveform.update_position`; cột dùng `WAVE_DIM`/`WAVE_PLAYED`; playhead vẽ cả ở 0 s; bỏ cập nhật trùng trong `_tick`/`messages` |
| Hội thoại không nhập được `.docx` | Page chỉ có “Dán mẫu” | Thêm nút **Mở tệp** (`.docx/.txt`), tách `load_script_file()` để test |
| Lịch sử chỉ có tab Đọc văn bản | Hàng loạt/Ghép nhạc không gọi `history.add` | Hàng loạt ghi từng file audio; Ghép nhạc ghi 1 mục; cả hai cập nhật `_export_history` (“Gần đây”) |
| Hội thoại (đã có lịch sử) | — | Bổ sung cập nhật `_export_history`; probe xác nhận |

- `probe_dialogue`, `probe_merge_page`, `probe_batch` thêm kiểm tra waveform + lịch sử, tất cả **OK**.
- `pytest` **236/236**; `probe_shell/pages/tags_history/license/ui_flow` **OK**.
- Rebuild `3.5.0`: 84 file, `update_3.5.0.zip` **29,96 MB**, `probe_obfuscated_build` **OK**.
- HDSD bổ sung mục “Mở tệp .docx/.txt” và “Lịch sử mọi tab”.

### P5.2 — lịch sử chỉ metadata (03/11/2026)

| Việc | Chi tiết |
|---|---|
| `core/history.py` schema v2 | `path` tuyệt đối tới file người dùng xuất; **không sao chép audio**; `remove/clear` chỉ bỏ mục, không xoá file; `prune` theo 200 mục, bỏ ngưỡng 500 MB/1 GB |
| Migration | Mục schema cũ (`audio_file`) **tự xoá một lần**: chỉ xoá file trong `history/`, bỏ mục legacy, ghi marker `.migrated_v2`, ghi lại `migration_summary` |
| UI Lịch sử | Summary “không tốn thêm dung lượng”; ghi chú lịch sử chỉ lưu thông tin; badge **“Thiếu file”** khi file gốc bị di chuyển/xoá; xoá mục/clear không đụng audio |
| Test | `tests/test_history.py` viết lại **15 test**; `probe_tags_history` xác nhận `dung_file_goc=True, khong_ban_sao=True`, xoá mục vẫn còn file |
| Tài liệu | README + HDSD cập nhật mô tả metadata-only |

Tổng `pytest`: **237 test**. `probe_tags_history`, `probe_pages`, `probe_dialogue`, `probe_merge_page`, `probe_batch` **OK**.

### P5.3 — trạng thái player theo tab + tốc độ Hội thoại (03/11/2026)

| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| Chuyển tab bị sai thời gian/waveform (vd. văn bản 1:54 → hội thoại 4:44 → văn bản vẫn 4:44) | Mỗi page chỉ đổi handler, không khôi phục source/duration riêng; tab Đọc văn bản không dừng audio khi rời tab | `TextPage.on_hide` pause; `on_show` khôi phục source/duration/position/speed; `DialoguePage.on_show` khôi phục hoặc `bar.clear()`; `MergePage` khôi phục preview hoặc clear |
| Tốc độ Hội thoại không đổi | Handler chỉ hiện thông báo; render cố định `speed=1.0` | Thêm `_on_speed_change` + time-stretch nền (base/play store, `timeline.scaled`), giữ vị trí khi đang phát, xuất file theo bản đã áp |
| Probes | — | `probe_tab_state` mới: văn bản ↔ hội thoại 2 vòng, tab rỗng clear, 1.0→1.5→1.0 |

Kết quả: `pytest` **237/237**; `probe_tab_state`, `probe_dialogue`, `probe_merge_page`, `probe_pages`, `probe_shell`, `probe_tags_history` **OK**.

### Phát hành 3.5.1 (03/11/2026)

- ersion.py → **3.5.1**; HDSD Huong_dan_su_dung_V3_v3.5.1.docx.
- Build: 84 file / 32,7 MB; manifest dist\_release\manifests\3.5.1.json.
- Gói cập nhật **3.5.0 → 3.5.1**: dist\_release\update_3.5.0_to_3.5.1.zip
  - 29,98 MB, SHA256 148A6B6B92B1DCF522B02D44B702302FF0AE0D2FE754D256536985C64ED744B9
  - Payload 81 file = **toàn bộ 78 file .py** + exe + HDSD + runtime; 0 file xoá
  - An toàn với mọi bản 3.5.0 (kể cả bản cũ) vì code obfuscate đổi hash mỗi lần build.
- Test cài thử: copy 3.5.1 → hạ manifest về 3.5.0 → capnhat.ps1 -Quiet -NoLaunch
  → lên 3.5.1, backup 3.5.0_<timestamp> đầy đủ.
- probe_obfuscated_build **OK** (84 file khớp sha256, exe mở cửa sổ).

### P5.4 — scroll dự phòng cho page (10/11/2026)

| Việc | Chi tiết |
|---|---|
| `ScrollArea` | `ui/ui_kit.py`: body lấp đầy khung khi nội dung vừa (giữ nguyên grid/weight), tự hiện thanh cuộn 8 px khi có widget lòi khỏi đáy; gutter cố định nên ẩn/hiện không nhảy layout; tái dùng xử lý wheel lồng của CTk 6.0.0 |
| `Page` | `Page(scroll=True)` mặc định, mọi page dùng `ScrollArea` cho `body`; thêm `Page.refresh_layout()` |
| Cài đặt / Bản quyền | Tự cuộn ở 1024×640; Bản quyền khoá chiều cao tối thiểu card hướng dẫn để không bị bóp còn vài chục px |
| Cửa sổ | `minsize(1024, 640)`; size khởi tạo theo màn hình và căn giữa (vừa laptop 1366×768) |
| Probe | `probe_shell` thêm mốc 1024×640 + kiểm tra cuộn; `probe_scroll` mới: 9 page × 3 mốc, fallback 900×560, chống lặp layout khi rảnh |

Kết quả: `pytest` **237/237**; `probe_shell`, `probe_pages`, `probe_merge_page`,
`probe_dialogue`, `probe_scroll` **OK**.

### Việc tiếp theo

- **P1**: `SettingsPage`, `DictionaryPage`, `VoicesPage`, `LicensePage` (thay 4 dialog cũ).
- **P2**: `BatchPage`, `HistoryPage`.
- **P3**: `MergePage`.
- **P4**: `DialoguePage` + core/engine hội thoại.
- **P5**: `DialogShell` cho 3 modal + HDSD ảnh mới + build 3.5.0.
