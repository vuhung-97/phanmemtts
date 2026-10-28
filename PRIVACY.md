# CHÍNH SÁCH QUYỀN RIÊNG TƯ

**Phần mềm chuyển đổi văn bản thành giọng nói tự nhiên v3**
Phiên bản chính sách: **1** · Cập nhật: **28/10/2026**

## 1. Tóm tắt

Phần mềm chạy **hoàn toàn offline**. Không có bất kỳ dữ liệu nào được gửi
đến nhà phát triển hay bên thứ ba. Mọi văn bản, giọng nói và tệp âm thanh
đều nằm trên máy tính của bạn.

## 2. Dữ liệu được lưu trên máy bạn

Mọi dữ liệu dưới đây nằm trong `%LOCALAPPDATA%\PhanMemTTS\` (Windows):

| Dữ liệu | Tệp / thư mục | Mục đích | Xoá được? |
|---|---|---|---|
| Cấu hình | `app_settings.json` | độ chính xác model, số luồng CPU, chế độ lưu audio, trạng thái đồng ý điều khoản | Có |
| Bản quyền | `license.json`, `.state` | mã máy, mã kích hoạt, hạn dùng, mốc thời gian | Có (mất kích hoạt) |
| Lịch sử bản dựng | `history\` | bản sao tệp audio đã xuất + `index.json` | Có (trong app) |
| Từ điển phát âm | `pronunciation-dict.json` | cặp thay thế do bạn nhập | Có |
| Âm thanh tạm | `tmp\` | audio đang tổng hợp (chế độ lưu đĩa) | Tự xoá khi đóng app |

Ngoài ra, phần mềm ghi một khoá nhỏ trong registry
`HKCU\Software\PhanMemTTS` để chống đặt lại thời gian dùng thử.

**Không** lưu: nội dung văn bản bạn dán vào, lịch sử clipboard, hay thông
tin cá nhân nào khác.

## 3. Không có kết nối mạng

- Model TTS, model chuyển đổi giọng và âm thanh mẫu được **chép sẵn** trong
  bộ cài.
- Phần mềm đặt `HF_HUB_OFFLINE=1` và tắt telemetry của thư viện tải model.
- Không có tài khoản, không có đăng nhập, không có máy chủ.

## 4. Chia sẻ dữ liệu

Không chia sẻ. Trường hợp duy nhất dữ liệu rời khỏi máy là khi **bạn chủ
động** gửi mã máy (10 ký tự) cho nhà phát triển để xin mã kích hoạt. Mã máy
là giá trị băm một chiều từ thông tin phần cứng, không chứa tên máy, tên
người dùng hay dữ liệu cá nhân.

## 5. Trẻ em

Phần mềm không hướng tới trẻ em và không thu thập dữ liệu của bất kỳ ai.

## 6. Quyền của bạn

Bạn có thể xoá toàn bộ dữ liệu cục bộ bằng cách xoá thư mục
`%LOCALAPPDATA%\PhanMemTTS\` và khoá registry nêu trên. Lưu ý: xoá
`license.json` sẽ làm mất kích hoạt hiện tại.

## 7. Thay đổi chính sách

Nếu chính sách thay đổi, phiên bản mới sẽ được phát hành kèm phần mềm và
hiển thị lại trong hộp thoại điều khoản.

## 8. Liên hệ

Mọi câu hỏi về quyền riêng tư, vui lòng liên hệ nhà phát triển qua kênh hỗ
trợ đã cung cấp khi mua/giao phần mềm.
