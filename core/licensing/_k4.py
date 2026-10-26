"""Mảnh 4/4 của secret ký mã kích hoạt.

GIÁ TRỊ DƯỚI ĐÂY LÀ GIẢ (dùng cho dev và test). Bản build chính thức được
tools/inject_secret.py ghi đè bằng mảnh thật lấy từ
tools/license_tool/keys/license_secret.bin (file này KHÔNG nằm trong git).
"""

PART = bytes.fromhex("3132333435363738")
