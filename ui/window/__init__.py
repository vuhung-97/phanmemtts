"""Các mixin tách từ `MainWindow`.

Mỗi mixin là lớp thuần (không `__init__`), dùng chung state với `MainWindow`.
Việc tách file để mỗi module nằm dưới giới hạn 32 KB của PyArmor bản miễn phí.
"""

from ui.window.convert import ConvertMixin
from ui.window.export import ExportMixin
from ui.window.tools import ToolsMixin

__all__ = ["ConvertMixin", "ExportMixin", "ToolsMixin"]
