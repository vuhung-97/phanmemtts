"""Bộ thành phần giao diện dùng chung (design system) cho shell SaaS.

Mục tiêu: mọi page/dialog chỉ dùng các factory ở đây, không tự khai báo
màu / viền / kích thước nút rải rác.
"""

from __future__ import annotations

from typing import Callable, Iterable

import customtkinter as ctk

from ui import theme

# ── Kích thước chuẩn ──
HEIGHT_SM = 30
HEIGHT_MD = 36
HEIGHT_LG = 40

_VARIANTS = {
    "primary": dict(fg_color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER,
                    text_color="#FFFFFF", border_width=0),
    "secondary": dict(fg_color=theme.SURFACE, hover_color=theme.BUTTON_HOVER,
                      text_color=theme.TEXT, border_width=1,
                      border_color=theme.BORDER),
    "ghost": dict(fg_color="transparent", hover_color=theme.HOVER_BG,
                  text_color=theme.TEXT_DIM, border_width=0),
    "soft": dict(fg_color=theme.PRIMARY_SOFT, hover_color="#DBEAFE",
                 text_color=theme.PRIMARY, border_width=0),
    "danger": dict(fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER,
                   text_color="#FFFFFF", border_width=0),
    "danger-soft": dict(fg_color=theme.DANGER_SOFT, hover_color="#FECACA",
                        text_color=theme.DANGER, border_width=0),
}


class Button(ctk.CTkButton):
    """Nút theo chuẩn: variant primary/secondary/ghost/soft/danger, size sm/md/lg."""

    def __init__(self, master, text: str = "", variant: str = "secondary",
                 size: str = "md", command: Callable | None = None,
                 width: int = 0, **kwargs) -> None:
        style = dict(_VARIANTS.get(variant, _VARIANTS["secondary"]))
        style.update(kwargs)
        height = {"sm": HEIGHT_SM, "md": HEIGHT_MD, "lg": HEIGHT_LG}.get(
            size, HEIGHT_MD)
        super().__init__(
            master, text=text, command=command, width=width, height=height,
            corner_radius=theme.RADIUS_SM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            **style,
        )


class IconButton(Button):
    """Nút icon nhỏ (sidebar thu gọn, hàng bảng)."""

    def __init__(self, master, text: str, command: Callable | None = None,
                 width: int = 32, height: int = 28, **kwargs) -> None:
        super().__init__(master, text=text, variant="ghost", size="sm",
                         command=command, width=width, **kwargs)
        self.configure(height=height, font=(theme.FONT_FAMILY,
                                            theme.FONT_SIZE, "normal"))


class Card(ctk.CTkFrame):
    """Khối nội dung trắng, viền nhẹ, bo góc 12, có vùng đệm trong.

    Đặt widget con vào ``card.content`` (không phải ``card``) để luôn cách
    viền đúng ``padding`` px.
    """

    def __init__(self, master, padding: int = theme.SPACE_LG, **kwargs) -> None:
        kwargs.setdefault("fg_color", theme.SURFACE)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.BORDER)
        kwargs.setdefault("corner_radius", theme.RADIUS_MD)
        super().__init__(master, **kwargs)
        self._padding = padding
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=padding, pady=padding)

    @property
    def padding(self) -> int:
        return self._padding


class ScrollArea(ctk.CTkScrollableFrame):
    """Vùng cuộn dọc cho nội dung page.

    - Khi nội dung vừa khung: ép inner frame cao bằng khung nhìn để grid/weight
      hoạt động y như ``CTkFrame`` cũ (editor, danh sách vẫn lấp đầy).
    - Khi có widget/card bên trong lòi khỏi đáy: mới bật thanh cuộn và cho
      inner frame cao bằng chiều cao tự nhiên.
    - Luôn chừa gutter cố định nên ẩn/hiện thanh cuộn không làm nhảy layout.
    """

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("scrollbar_fg_color", theme.BG)
        kwargs.setdefault("scrollbar_button_color", theme.BG)
        kwargs.setdefault(
            "scrollbar_button_hover_color", theme.SCROLL_BUTTON_HOVER)
        super().__init__(master, orientation="vertical", **kwargs)
        self._scrollbar.configure(width=8)
        self._parent_frame.grid_columnconfigure(1, minsize=theme.SCROLL_GUTTER)
        self._bar_visible = False
        self._syncing = False
        self._job = None
        self._last_key: tuple[int, int, int] | None = None
        self._force = True
        self._parent_frame.bind("<Map>", self._schedule, add="+")
        self._parent_canvas.bind("<Configure>", self._schedule, add="+")
        self.bind("<Configure>", self._schedule, add="+")

    # ── API cho page/probe ──

    @property
    def scrollbar_visible(self) -> bool:
        return self._bar_visible

    def refresh_layout(self) -> None:
        """Gọi sau khi thêm/bớt widget cấp 1 (card) trong body."""
        self._force = True
        self._schedule()

    def scroll_to_top(self) -> None:
        self._parent_canvas.yview_moveto(0.0)

    def scroll_to_bottom(self) -> None:
        self._parent_canvas.yview_moveto(1.0)

    # ── layout ──

    def _schedule(self, _event=None) -> None:
        if self._syncing or self._job is not None:
            return
        try:
            self._job = self.after_idle(self._apply)
        except Exception:
            self._job = None

    def _apply(self) -> None:
        self._job = None
        if not self.winfo_exists():
            return
        canvas = self._parent_canvas
        height = canvas.winfo_height()
        width = canvas.winfo_width()
        if height <= 1 or width <= 1:
            return
        key = (width, height, self.winfo_reqheight())
        if key == self._last_key and not self._force:
            return
        self._last_key = key
        self._force = False
        self._syncing = True
        try:
            # Đo lại ở đúng chiều cao khung nhìn (grid co các hàng có weight).
            self._set_height(height)
            self.update_idletasks()
            overflow = self._overflows(height)
            target = height
            if overflow:
                target = max(height, self.winfo_reqheight(),
                             self._content_bottom())
            self._set_height(target)
            self._toggle_bar(overflow)
            if not overflow:
                canvas.yview_moveto(0.0)
            self.update_idletasks()
            canvas.configure(
                scrollregion=canvas.bbox("all") or (0, 0, width, target))
        finally:
            self._syncing = False

    def _set_height(self, height: int) -> None:
        try:
            self._parent_canvas.itemconfigure(
                self._create_window_id, height=max(1, int(height)))
        except Exception:
            pass

    def _overflows(self, height: int) -> bool:
        for child in self.winfo_children():
            if not child.winfo_ismapped():
                continue
            if self._subtree_overflows(child, height):
                return True
        return False

    def _subtree_overflows(self, widget, height: int) -> bool:
        """Widget (hoặc con của nó) có lòi khỏi khung nhìn không.

        Vùng cuộn lồng bên trong được coi là "cố ý cắt" nên bỏ qua phần nội
        dung của nó, chỉ kiểm tra bản thân khung cuộn có nằm gọn không.
        """
        top = self.winfo_rooty()
        if isinstance(widget, ctk.CTkScrollableFrame):
            host = widget._parent_frame
            if not host.winfo_ismapped():
                return False
            bottom = host.winfo_rooty() - top + host.winfo_height()
            return bottom > height + 2
        if widget.winfo_ismapped():
            bottom = widget.winfo_rooty() - top + widget.winfo_height()
            if bottom > height + 2:
                return True
        for child in widget.winfo_children():
            if self._subtree_overflows(child, height):
                return True
        return False

    def _content_bottom(self) -> int:
        top = self.winfo_rooty()
        bottom = 0
        for child in self.winfo_children():
            if not child.winfo_ismapped():
                continue
            host = (child._parent_frame
                    if isinstance(child, ctk.CTkScrollableFrame) else child)
            bottom = max(bottom, host.winfo_rooty() - top + host.winfo_height())
        return bottom

    def _toggle_bar(self, visible: bool) -> None:
        if visible == self._bar_visible:
            return
        self._bar_visible = visible
        color = theme.SCROLL_BUTTON if visible else theme.BG
        self._scrollbar.configure(button_color=color)
        self._scrollbar.configure(
            button_hover_color=(theme.SCROLL_BUTTON_HOVER
                                if visible else theme.BG))

    def destroy(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        super().destroy()


class Badge(ctk.CTkLabel):
    """Nhãn trạng thái nhỏ (xám/xanh/vàng/đỏ)."""

    TONES = {
        "neutral": (theme.SURFACE_2, theme.TEXT_DIM),
        "info": (theme.PRIMARY_SOFT, theme.PRIMARY),
        "success": (theme.SUCCESS_SOFT, theme.SUCCESS),
        "warning": (theme.WARNING_SOFT, theme.WARNING),
        "danger": (theme.DANGER_SOFT, theme.DANGER),
    }

    def __init__(self, master, text: str = "", tone: str = "neutral",
                 **kwargs) -> None:
        bg, fg = self.TONES.get(tone, self.TONES["neutral"])
        kwargs.setdefault("height", 24)
        super().__init__(
            master, text=text, fg_color=bg, text_color=fg, corner_radius=theme.RADIUS_SM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            padx=0, **kwargs,
        )

    def set_tone(self, tone: str) -> None:
        bg, fg = self.TONES.get(tone, self.TONES["neutral"])
        self.configure(fg_color=bg, text_color=fg)


class PageHeader(ctk.CTkFrame):
    """Tiêu đề page: title + subtitle + vùng nút hành động bên phải."""

    def __init__(self, master, title: str, subtitle: str = "",
                 **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=0, column=0, sticky="ew")
        box.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            box, text=title, anchor="w", justify="left",
            font=(theme.FONT_FAMILY, 19, "bold"), text_color=theme.TEXT,
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            box, text=subtitle, anchor="w", justify="left",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        )
        self.subtitle_label.grid(row=1, column=0, pady=(2, 0), sticky="w")
        if not subtitle:
            self.subtitle_label.grid_remove()

        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=0, column=1, sticky="e")

    def set_subtitle(self, text: str) -> None:
        if text:
            self.subtitle_label.configure(text=text)
            self.subtitle_label.grid()
        else:
            self.subtitle_label.grid_remove()

    def add_action(self, widget) -> None:
        widget.pack(side="left", padx=(theme.SPACE_SM, 0))


class SectionTitle(ctk.CTkFrame):
    """Tiêu đề mục nhỏ + gợi ý."""

    def __init__(self, master, title: str, hint: str = "", **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        ctk.CTkLabel(
            self, text=title, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).pack(side="left")
        if hint:
            ctk.CTkLabel(
                self, text=hint, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
                text_color=theme.TEXT_DIM,
            ).pack(side="left", padx=(theme.SPACE_SM, 0))


class Field(ctk.CTkFrame):
    """Nhãn + widget + gợi ý/lỗi (dọc)."""

    def __init__(self, master, label: str, widget, hint: str = "",
                 **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self, text=label, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2, "bold"),
            text_color=theme.TEXT_DIM,
        ).grid(row=0, column=0, sticky="w")
        widget.grid(row=1, column=0, pady=(4, 0), sticky="ew")
        self.hint_label = ctk.CTkLabel(
            self, text=hint, anchor="w", justify="left",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT_DIM,
        )
        self.hint_label.grid(row=2, column=0, pady=(3, 0), sticky="w")
        if not hint:
            self.hint_label.grid_remove()

    def set_hint(self, text: str, error: bool = False) -> None:
        self.hint_label.configure(
            text=text, text_color=theme.ERROR if error else theme.TEXT_DIM)
        self.hint_label.grid() if text else self.hint_label.grid_remove()


class EmptyState(ctk.CTkFrame):
    """Trạng thái rỗng: icon + tiêu đề + gợi ý + nút."""

    def __init__(self, master, icon: str, title: str, hint: str = "",
                 action: ctk.CTkBaseClass | None = None, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        ctk.CTkLabel(self, text=icon, font=(theme.FONT_FAMILY, 28),
                     text_color=theme.TEXT_DIM).pack(pady=(theme.SPACE_XL, theme.SPACE_SM))
        ctk.CTkLabel(self, text=title, font=(theme.FONT_FAMILY, 15, "bold"),
                     text_color=theme.TEXT).pack()
        if hint:
            ctk.CTkLabel(self, text=hint, font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                         text_color=theme.TEXT_DIM, wraplength=420,
                         justify="center").pack(pady=(theme.SPACE_XS, 0))
        if action is not None:
            action.pack(pady=(theme.SPACE_MD, 0))


class Table(ctk.CTkFrame):
    """Bảng đơn giản: header + hàng, cột co giãn theo weight."""

    def __init__(self, master, columns: Iterable[tuple[str, str, int]],
                 on_row_click: Callable[[int], None] | None = None,
                 **kwargs) -> None:
        kwargs.setdefault("fg_color", theme.SURFACE)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.BORDER)
        kwargs.setdefault("corner_radius", theme.RADIUS_MD)
        super().__init__(master, **kwargs)
        self._columns = list(columns)
        self._on_row_click = on_row_click
        self._rows: list[ctk.CTkFrame] = []
        for idx, (_, _, weight) in enumerate(self._columns):
            self.grid_columnconfigure(idx, weight=weight)

    def set_rows(self, rows: list[list[str]]) -> None:
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        # header
        for idx, (label, _, _) in enumerate(self._columns):
            ctk.CTkLabel(
                self, text=label, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2, "bold"),
                text_color=theme.TEXT_DIM,
            ).grid(row=0, column=idx, padx=theme.SPACE_MD,
                   pady=(theme.SPACE_SM, theme.SPACE_XS), sticky="w")
        for r, values in enumerate(rows, start=1):
            frame = ctk.CTkFrame(self, fg_color="transparent")
            frame.grid(row=r, column=0, columnspan=len(self._columns),
                       sticky="ew")
            for idx, (_, _, weight) in enumerate(self._columns):
                frame.grid_columnconfigure(idx, weight=weight)
                text = values[idx] if idx < len(values) else ""
                ctk.CTkLabel(
                    frame, text=text, anchor="w",
                    font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                    text_color=theme.TEXT,
                ).grid(row=0, column=idx, padx=theme.SPACE_MD,
                       pady=theme.SPACE_XS, sticky="w")
                if self._on_row_click is not None:
                    for child in frame.winfo_children():
                        child.bind("<Button-1>",
                                   lambda _e, i=r - 1: self._on_row_click(i))
            self._rows.append(frame)


class Tooltip:
    """Tooltip nhỏ cho sidebar thu gọn."""

    def __init__(self, widget, text: str, delay_ms: int = 450) -> None:
        self._widget = widget
        self._text = text
        self._delay = delay_ms
        self._job = None
        self._tip: ctk.CTkToplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._job = self._widget.after(self._delay, self._show)

    def _cancel(self) -> None:
        if self._job is not None:
            try:
                self._widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _show(self) -> None:
        if self._tip is not None:
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 6
        y = self._widget.winfo_rooty() + 4
        tip = ctk.CTkToplevel(self._widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tip.configure(fg_color=theme.TEXT)
        ctk.CTkLabel(
            tip, text=self._text, text_color="#FFFFFF",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        ).pack(padx=8, pady=3)
        self._tip = tip

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None
