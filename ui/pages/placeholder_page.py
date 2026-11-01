from __future__ import annotations

from ui.shell.page import Page
from ui.ui_kit import EmptyState


class PlaceholderPage(Page):
    """Trang tạm cho chức năng chưa port xong (P0)."""

    def __init__(self, master, ctx, page_id: str, title: str,
                 note: str = "Chức năng này sẽ được chuyển sang giao diện mới "
                             "trong bước tiếp theo.", **kwargs) -> None:
        super().__init__(master, ctx, page_id=page_id, title=title, **kwargs)
        EmptyState(
            self.body, icon="🚧", title=title,
            hint=note,
        ).grid(row=0, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
