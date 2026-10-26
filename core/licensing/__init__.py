"""Lõi bản quyền offline (mã máy + mã kích hoạt 15 ký tự).

Các module sẽ có trong gói này (P1):
    fingerprint.py  - đọc MachineGuid + Volume serial, sinh mã máy 10 ký tự
    shortcode.py    - mã hoá/giải mã + xác thực mã kích hoạt 15 ký tự
    secret.py       - ghép 4 mảnh secret (build-time injection)
    store.py        - license.json / .state / registry
    trial.py        - dùng thử 7 ngày
    guard.py        - trạng thái bản quyền + điểm chặn

KHÔNG chứa secret thật trong repo: _k1..4.py chỉ là placeholder, giá trị thật
được tools/inject_secret.py ghi vào cây source tạm ngay trước khi obfuscate.
"""
