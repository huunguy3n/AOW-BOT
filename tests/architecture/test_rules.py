"""F2: luat phu thuoc (docs/architecture/dependency-rules.md). import-linter kiem D1-D8; cac test AST o day kiem
D9 (khong trang thai global co the thay doi), D10 (import trong ham phai co ly do), D1 bo sung (domain khong doc
dong ho / file / ngau nhien)."""
import ast
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "aowbot"
FILES = sorted(SRC.rglob("*.py"))
DOMAIN = [p for p in FILES if "domain" in p.parts]


def _tree(p):
    return ast.parse(p.read_text(encoding="utf-8"), filename=str(p))


def _rel(p):
    return p.relative_to(ROOT).as_posix()


@pytest.mark.skipif(shutil.which("lint-imports") is None, reason="chua cai import-linter (pip install -e .[dev])")
def test_import_contracts():
    r = subprocess.run(["lint-imports"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", check=False, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout[-3000:]


MUTABLE = (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)


@pytest.mark.parametrize("path", FILES, ids=_rel)
def test_no_module_level_mutable_state(path):
    bad = []
    for node in _tree(path).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, MUTABLE):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            bad += [t.id for t in targets if isinstance(t, ast.Name)]
        if isinstance(node, ast.Global):
            bad += node.names
    # hang so UPPER_CASE dang dict/list chi doc van bi cam: dung tuple / MappingProxyType / frozenset
    assert not bad, f"{_rel(path)}: trang thai cap module co the thay doi {bad}"


@pytest.mark.parametrize("path", FILES, ids=_rel)
def test_function_level_imports_have_reason(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    bad = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    prev = lines[sub.lineno - 2] if sub.lineno >= 2 else ""
                    if "# lazy:" not in prev and "# lazy:" not in lines[sub.lineno - 1]:
                        bad.append(sub.lineno)
    assert not bad, f"{_rel(path)}: import trong ham khong co comment '# lazy:' o dong {bad}"


FORBIDDEN_CALLS = {("time", "time"), ("time", "monotonic"), ("time", "perf_counter"), ("datetime", "now"),
                   ("datetime", "today")}


@pytest.mark.parametrize("path", DOMAIN, ids=_rel)
def test_domain_has_no_clock_file_or_random(path):
    tree = _tree(path)
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "open":
                bad.append(f"open() dong {node.lineno}")
            attr = isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
            if attr and (f.value.id, f.attr) in FORBIDDEN_CALLS:
                bad.append(f"{f.value.id}.{f.attr}() dong {node.lineno}")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            bad += [f"import {m}" for m in mods if m.split(".")[0] in ("random", "time", "datetime", "os", "pathlib")]
    assert not bad, f"{_rel(path)}: {bad}"


def test_rules_cover_some_files():
    assert FILES and DOMAIN
