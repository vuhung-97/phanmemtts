"""Runtime hook cho bản v3 modular (app_v3_modular.spec).

Code app (core/engine/audio/ui/version) KHÔNG nhúng vào EXE mà nằm rời dạng
.py đã obfuscate cạnh EXE. Hook này chèn thư mục chứa EXE vào đầu sys.path để
frozen importer tìm thấy các module đó (thay cho _MEIPASS).
"""

import os
import sys

_base = os.path.dirname(os.path.abspath(sys.executable))
if _base not in sys.path:
    sys.path.insert(0, _base)
