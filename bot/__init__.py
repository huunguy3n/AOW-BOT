# Ma cu duoc phep dung aowbot.domain (luat D7, docs/architecture/dependency-rules.md). Dat src/ vao sys.path
# o day (mot cho duy nhat) de main.py, web va tools/* chay duoc ca khi chua `pip install -e .`.
import os as _os
import sys as _sys

_SRC = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src")
if _os.path.isdir(_SRC) and _SRC not in _sys.path:
    _sys.path.append(_SRC)
