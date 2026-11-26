"""P13g-1: 26/11 09:19 '#3 Instance 3 loi: module aowbot.domain.builders has no attribute FillState' - lan chay 09:17
thua huong PYTHONPATH tro toi worktree P13e cu. Ma cua chinh repo dang chay phai thang PYTHONPATH."""
import glob
import os
import re
import subprocess
import sys

import main
from aowbot.domain import builders
from aowbot.domain.builders import FillState

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_fill_state_import_and_use():
    fs = FillState(2, 1)
    fs.attempt(0)
    assert not fs.decide(busy=1, idle=0, started=1)          # het tho ranh
    assert fs.decide(busy=0, idle=1, started=1)              # tho vua xong -> chen buoc xay
    assert not fs.decide(busy=0, idle=1, started=1)          # chen ma khong xay duoc gi -> khong lap
    assert fs.decide(busy=0, idle=1, started=1, new_resources=True)
    assert not fs.decide(busy=0, idle=1, started=2)          # het tran so lan chen


def test_every_builders_dom_call_exists():
    used = set()
    for f in glob.glob(os.path.join(ROOT, "bot", "**", "*.py"), recursive=True):
        with open(f, encoding="utf-8") as fh:
            used |= set(re.findall(r"builders_dom\.(\w+)", fh.read()))
    assert "FillState" in used
    assert [n for n in sorted(used) if not hasattr(builders, n)] == []


def test_stale_pythonpath_does_not_shadow_repo(tmp_path):
    """Gia lap lan chay loi: PYTHONPATH tro toi 1 ban aowbot cu khong co FillState; nap main.py nhu 'python main.py'."""
    dom = tmp_path / "src" / "aowbot" / "domain"
    dom.mkdir(parents=True)
    (dom.parent / "__init__.py").write_text("", encoding="utf-8")
    (dom / "__init__.py").write_text("", encoding="utf-8")
    (dom / "builders.py").write_text("FILL_STEPS = ()\n", encoding="utf-8")
    code = ("import runpy; runpy.run_path('main.py', run_name='probe'); "
            "from aowbot.domain import builders as b; b.FillState(1, 1); print(b.__file__)")
    env = {**os.environ, "PYTHONPATH": str(tmp_path / "src")}
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                       timeout=120, check=False)
    assert r.returncode == 0, r.stderr
    got = os.path.normcase(r.stdout.strip())
    assert got.startswith(os.path.normcase(os.path.join(ROOT, "src")))


def test_check_import_paths_flags_foreign_copy(tmp_path):
    own = os.path.join(ROOT, "src", "aowbot", "__init__.py")
    assert main.check_import_paths(ROOT, environ={}, module_file=own)
    other = str(tmp_path / "src" / "aowbot" / "__init__.py")
    assert not main.check_import_paths(ROOT, environ={"PYTHONPATH": str(tmp_path)}, module_file=other)


def test_run_bat_clears_pythonpath_before_python():
    with open(os.path.join(ROOT, "run.bat"), encoding="ascii") as f:
        lines = [ln.strip() for ln in f.read().splitlines()]
    py = next(i for i, ln in enumerate(lines) if ln.startswith("python "))
    assert lines.index('set "PYTHONPATH="') < py
    assert "setlocal" in lines[:py]                      # khong sua bien cua cua so goi
