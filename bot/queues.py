"""Q0: doc HANG CHO o cot icon trai man thanh pho (chu du an 2026-11-21: "luon dam bao ... xay dung, nghien cuu,
huan luyen luon hoat dong, chi khi toi gioi han").

Cot trai hien san 'dang chay/tong' cho tho xay (bua), nghien cuu (nguyen tu), huan luyen (may bay): 1 anh thanh pho
= trang thai ca 3 hang cho, khong can mo bang. Icon chua mo khoa (TK cap thap) -> khong co trong ket qua.

P2 (PM 2026-11-23): Tesseract khong doc duoc "1/1" (so 1 manh), "3/3" tren nen sang -> doc theo 3 lop:
  1. ANH CHU SO (templates/qdigits/0..3, slash; cat tu anh that) - khop xam, ~1 ms, khong can Tesseract.
  2. OCR nhieu cach xu ly anh roi BO PHIEU (cach cu).
  3. CHAM DO tren icon = hang cho dang RANH (game chi hien cham khi con cho trong): khong doc duoc so ma thay cham
     va biet tong (nghien cuu luon 1, hoac tong da biet tu lan truoc) -> (tong - 1, tong). Khong thay cham thi KHONG
     ket luan (farm cap thap co luc khong hien cham).
"""
import os
import re
from collections import Counter

import cv2
import numpy as np

from bot import ocr
from bot.badges import red_dots

ICONS = {"build": "build/icon_builder", "research": "research/icon_queue", "train": "train/queue_icon"}
COLUMN = (0, 90, 120, 320)           # cot icon trai (540x960)
COUNT_OFF = (27, -15, 42, 24)        # vung so 'x/y' tinh tu tam icon
GLYPH_OFF = (20, -20, 56, 34)        # vung tim anh chu so (rong hon COUNT_OFF: vi tri chu lech theo icon)
DOT_OFF = (5, -38, 45, 30)           # vung cham do (goc phai tren icon)
GLYPH_TH = 0.62                      # nguong khop anh chu so (TM_CCOEFF_NORMED tren anh xam)
KNOWN_TOTAL = {"research": 1}        # chi 1 hang nghien cuu (chu du an 2026-11-21)
# thu tu: cach hay dung truoc; dung som khi 1 gia tri du phieu (moi lan OCR ~100-150 ms)
VARIANTS = (dict(scale=4), dict(scale=3, bright=120), dict(scale=4, psm=8), dict(scale=4, bright=150, pad=15),
            dict(scale=4, bright=120, pad=15), dict(scale=4, pad=15))
_PAT = re.compile(r"^\s*(\d)\s*/\s*(\d)\s*$")
_GLYPHS = None
GLYPH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "qdigits")


def parse(s):
    m = _PAT.match(s or "")
    if not m:
        return None
    used, total = int(m.group(1)), int(m.group(2))
    return (used, total) if 1 <= total <= 6 and used <= total else None


def vote(texts, need=2):
    """Gia tri doc duoc nhieu nhat, it nhat `need` phieu va khong hoa -> (dang chay, tong) | None."""
    c = Counter(v for v in map(parse, texts) if v)
    top = c.most_common(2)
    if not top or top[0][1] < need or (len(top) > 1 and top[1][1] == top[0][1]):
        return None
    return top[0][0]


def glyphs(d=None):
    """{ky tu: [anh xam]} tu templates/qdigits (<so>[bien the].png, slash.png). Thieu thu muc -> {} (bo qua lop 1)."""
    global _GLYPHS
    if d is None and _GLYPHS is not None:
        return _GLYPHS
    out = load_glyph_dir(d or GLYPH_DIR)
    if d is None:
        _GLYPHS = out
    return out


def load_glyph_dir(path):
    """{ky tu: [anh xam]} tu 1 thu muc anh chu so (<so>[bien the].png, slash*.png). Thieu thu muc -> {}."""
    out = {}
    if os.path.isdir(path):
        for f in sorted(os.listdir(path)):
            if not f.endswith(".png"):
                continue
            g = cv2.imread(os.path.join(path, f), cv2.IMREAD_GRAYSCALE)
            if g is None:
                continue
            ch = "/" if f.startswith("slash") else f[0]
            if ch == "/" or ch.isdigit():
                out.setdefault(ch, []).append(g)
    return out


def read_glyphs(img, x, y, tpls=None, th=GLYPH_TH):
    """Lop 1 (ham thuan): doc 'x/y' bang anh chu so quanh icon tam (x, y) -> (dang chay, tong) | None."""
    dx, dy, w, h = GLYPH_OFF
    return read_glyph_box(img, (x + dx, y + dy, w, h), glyphs() if tpls is None else tpls, th, parse)


def read_glyph_box(img, box, tpls, th=GLYPH_TH, parse_fn=None):
    """Ham thuan dung chung (P2 hang cho, P3 'Hanh quan x/y'): doc 'so/so' trong vung box=(x, y, w, h) bang anh chu so.
    Moi ky tu: diem khop cao nhat tai moi cot; giu dinh khong trung nhau (cach >= 4px), xep theo x, phai co dang
    'so / so' cung hang (lech y <= 3px). parse_fn: chuoi 'a/b' -> gia tri | None (mac dinh parse cua hang cho)."""
    parse_fn = parse_fn or parse
    if not tpls or "/" not in tpls or not any(k.isdigit() for k in tpls):
        return None
    x, y, w, h = box
    x0, y0 = max(0, x), max(0, y)
    crop = img[y0:y + h, x0:x + w]
    if crop.size == 0:
        return None
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    hits = []
    for ch, lst in tpls.items():
        for t in lst:
            if g.shape[0] < t.shape[0] or g.shape[1] < t.shape[1]:
                continue
            r = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED)
            r = np.nan_to_num(r, nan=-1.0)
            ys, xs = np.where(r >= th)
            for yy, xx in zip(ys, xs):
                hits.append((float(r[yy, xx]), int(xx + t.shape[1] / 2), int(yy + t.shape[0] / 2), ch))
    hits.sort(reverse=True)
    keep = []
    for s, cx, cy, ch in hits:                           # NMS theo x: moi vi tri 1 ky tu (diem cao nhat)
        if all(abs(cx - k[1]) >= 4 for k in keep):
            keep.append((s, cx, cy, ch))
    keep.sort(key=lambda k: k[1])
    for i, k in enumerate(keep):
        if k[3] != "/" or i == 0 or i + 1 >= len(keep):
            continue
        a, b = keep[i - 1], keep[i + 1]
        if a[3] == "/" or b[3] == "/":
            continue
        if abs(a[2] - k[2]) > 3 or abs(b[2] - k[2]) > 3 or k[1] - a[1] > 10 or b[1] - k[1] > 10:
            continue
        v = parse_fn(f"{a[3]}/{b[3]}")
        if v:
            return v
    return None


def read_count(img, x, y):
    got = read_glyphs(img, x, y)
    if got:
        return got
    dx, dy, w, h = COUNT_OFF
    texts = []
    for va in VARIANTS:
        texts.append(ocr.text(img, (x + dx, y + dy, w, h), "0123456789/", **va))
        got = vote(texts)
        if got and Counter(map(parse, texts))[got] >= 2:
            return got
    return vote(texts)


def has_dot(img, x, y):
    """Cham do goc phai tren icon (x, y) = hang cho con cho trong."""
    dx, dy, w, h = DOT_OFF
    return bool(red_dots(img, (max(0, x + dx), max(0, y + dy), w, h)))


def resolve(val, dot, total=None):
    """Ket hop so doc duoc + cham do (ham thuan) -> (dang chay, tong) | None.
    - doc duoc va khong mau thuan -> giu; doc 'day' (x = y) ma co cham do -> sai, bo (None).
    - khong doc duoc + cham do + biet tong -> (tong - 1, tong) (it nhat 1 cho ranh)."""
    if val:
        if dot and val[0] >= val[1]:
            return None
        return val
    if dot and total:
        return (total - 1, total)
    return None


def read(v, img, totals=None):
    """-> {'build'|'research'|'train': (dang chay, tong) | None (thay icon, khong doc duoc so)}; icon khong thay
    thi khong co khoa. totals: {loai: tong da biet} (tu lan doc truoc) cho lop cham do."""
    out = {}
    for kind, tpl in ICONS.items():
        p = v.find(img, tpl, th=0.8, roi=COLUMN)
        if p:
            total = KNOWN_TOTAL.get(kind) or (totals or {}).get(kind)
            out[kind] = resolve(read_count(img, p[0], p[1]), has_dot(img, p[0], p[1]), total)
    return out


def idle(q):
    """So cho ranh cua 1 hang cho (None = khong biet)."""
    return None if not q else q[1] - q[0]
