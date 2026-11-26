# Ma cu duoc phep dung aowbot.domain (luat D7, docs/architecture/dependency-rules.md). Dat src/ vao sys.path
# o day (mot cho duy nhat) de main.py, web va tools/* chay duoc ca khi chua `pip install -e .`.
# P13g-1: src/ cua CHINH repo nay phai dung DAU sys.path. Truoc day them vao CUOI nen thua PYTHONPATH / ban cai
# editable tro toi thu muc khac: 26/11 09:17 bot chay voi aowbot cua worktree P13e cu (chua co builders.FillState).
import os as _os
import sys as _sys

_SRC = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src")
if _os.path.isdir(_SRC):
    while _SRC in _sys.path:
        _sys.path.remove(_SRC)
    _sys.path.insert(0, _SRC)
