from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image

from core.paths import resource_path
from ui import theme
from ui.ui_kit import Badge

_LOGO_PATH = Path(resource_path("logo/logo.jpg"))


class AppHeader(ctk.CTkFrame):
    """Header trên cùng: logo + tên app + version."""

    def __init__(self, master, app_name: str, version: str, **kwargs) -> None:
        kwargs.setdefault("fg_color", theme.SURFACE)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("height", theme.HEADER_HEIGHT)
        super().__init__(master, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)

        self._logo_image = None
        logo = ctk.CTkLabel(self, text="", width=36)
        logo.grid(row=0, column=0, padx=(theme.SPACE_LG, theme.SPACE_SM),
                  pady=theme.SPACE_SM)
        if _LOGO_PATH.exists():
            try:
                with Image.open(_LOGO_PATH) as image:
                    image.load()
                    rgb = image.convert("RGB")
                    self._logo_image = ctk.CTkImage(rgb, size=(30, 30))
                logo.configure(image=self._logo_image)
            except Exception:
                self._logo_image = None

        self.title_label = ctk.CTkLabel(
            self, text=app_name, anchor="w",
            font=(theme.FONT_FAMILY, 15, "bold"), text_color=theme.TEXT,
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            self, text="", width=theme.SPACE_MD,
        ).grid(row=0, column=2)

        self.version_badge = Badge(self, text=f"v{version}", tone="info")
        self.version_badge.grid(row=0, column=3, padx=(0, theme.SPACE_XL))
