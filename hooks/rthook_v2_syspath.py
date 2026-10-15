"""Runtime hook cho ban V2 modular (app_v2.spec).

Code app (core/engine/audio/ui/...) KHONG nhung vao EXE ma nam roi dang
.py canh EXE. Hook nay chen thu muc chua EXE vao dau sys.path de frozen
importer tim thay cac module source do (thay cho _MEIPASS).
"""

import os
import sys

_base = os.path.dirname(os.path.abspath(sys.executable))
if _base not in sys.path:
    sys.path.insert(0, _base)
