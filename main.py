from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui.main_window import MainWindow


def main() -> None:
    # Chế độ freemium: app luôn mở được; chưa kích hoạt thì chỉ khoá phần tạo
    # ra file (Xuất file / Ghép nhạc). Lần chạy đầu, MainWindow tự mở hộp
    # thoại kích hoạt (xem MainWindow._first_run_prompt).
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
