from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    # Kiểm tra bản quyền TRƯỚC khi nạp UI/model: chưa kích hoạt thì chỉ mở
    # hộp thoại kích hoạt (nhẹ), không nạp 600 MB model.
    from core.licensing import guard

    status = guard.check_startup()
    if not status.active:
        from ui.components.activation_dialog import ask_activation

        if not ask_activation(status=status):
            return

    from ui.main_window import MainWindow

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
