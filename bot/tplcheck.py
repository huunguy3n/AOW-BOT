"""Liet ke anh mau code can ma chua co (dung chung cho `main.py --check` va `tools/snap.py todo`).

Quet chuoi "nhom/ten" trong bot/**/*.py voi nhom = thu muc con cua templates/, cong them anh mau
sinh dong (digits/0-9, gather/lv/N, tab mo theo priority, tuyen rewards/daily).
"""
import os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(BASE, "templates")


def needed(cfg):
    groups = sorted(d for d in os.listdir(TPL) if os.path.isdir(os.path.join(TPL, d)))
    pat = re.compile(r'"((?:%s)/[a-z0-9_/]+)"' % "|".join(map(re.escape, groups)))
    names = set()
    for root, _, files in os.walk(os.path.join(BASE, "bot")):
        for fn in files:
            if fn.endswith(".py"):
                names |= set(pat.findall(open(os.path.join(root, fn), encoding="utf-8").read()))
    g = cfg.get("gather", {})
    for r in g.get("priority", []):
        names.add(f"gather/tab_{r}")
    if g.get("ocr", "auto") in ("auto", "glyphs"):
        # P3: "Hanh quan x/y" doc bang templates/mdigits (cat tu anh that; 0/6-9 chua gap: khung an khi 0 doi, toi da 5 doi)
        names |= {f"mdigits/{d}" for d in "12345"} | {"mdigits/slash"}
    if g.get("ocr", "auto") == "digits":     # bo du phong cu: chi bat buoc khi chon rieng ocr: digits
        names |= {f"digits/{d}" for d in "0123456789"} | {"digits/slash"}
    for n in range(g.get("min_level", 1), g.get("max_level", 6) + 1):
        names.add(f"gather/lv/{n}")
    mods = cfg.get("modules", {})
    if mods.get("rewards"):
        for r in cfg.get("rewards", {}).get("routes", []):
            if not os.path.exists(os.path.join(TPL, "rewards", r, "once_1.png")):
                names.add(f"rewards/{r}/claim_1")
            if r != "city":
                names.add(f"rewards/{r}/open_1")
    if mods.get("daily"):
        names |= {"daily/open_1", "daily/claim_1", "daily/chest_1", "daily/btn_chest_claim"}
    if mods.get("rewards") or mods.get("daily"):
        names |= {"common/btn_confirm", "common/tap_to_continue"}
    return {n for n in names if not n.endswith(("_", "/"))}


def missing(cfg, group=None):
    """-> (so anh mau can, danh sach thieu da sap xep). group: chi lay 1 nhom (vd 'research')."""
    names = needed(cfg)
    if group:
        names = {n for n in names if n.startswith(group.rstrip("/") + "/")}
    miss = sorted(n for n in names if not os.path.exists(os.path.join(TPL, n + ".png")))
    return len(names), miss
