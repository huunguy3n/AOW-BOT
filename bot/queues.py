"""Q0: doc HANG CHO o cot icon trai man thanh pho (chu du an 2026-11-21: "luon dam bao ... xay dung, nghien cuu,
huan luyen luon hoat dong, chi khi toi gioi han").

Cot trai hien san 'dang chay/tong' cho tho xay (bua), nghien cuu (nguyen tu), huan luyen (may bay): 1 anh thanh pho
= trang thai ca 3 hang cho, khong can mo bang. Icon chua mo khoa (TK cap thap) -> khong co trong ket qua.
So nho (chu kem tren nen trong suot, phia sau la cong trinh) -> OCR nhieu cach xu ly anh roi BO PHIEU.
"""
import re
from collections import Counter

from bot import ocr

ICONS = {"build": "build/icon_builder", "research": "research/icon_queue", "train": "train/queue_icon"}
COLUMN = (0, 90, 120, 320)           # cot icon trai (540x960)
COUNT_OFF = (27, -15, 42, 24)        # vung so 'x/y' tinh tu tam icon
# thu tu: cach hay dung truoc; dung som khi 1 gia tri du phieu (moi lan OCR ~100-150 ms)
VARIANTS = (dict(scale=4), dict(scale=3, bright=120), dict(scale=4, psm=8), dict(scale=4, bright=150, pad=15),
            dict(scale=4, bright=120, pad=15), dict(scale=4, pad=15))
_PAT = re.compile(r"^\s*(\d)\s*/\s*(\d)\s*$")


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


def read_count(img, x, y):
    dx, dy, w, h = COUNT_OFF
    texts = []
    for va in VARIANTS:
        texts.append(ocr.text(img, (x + dx, y + dy, w, h), "0123456789/", **va))
        got = vote(texts)
        if got and Counter(map(parse, texts))[got] >= 2:
            return got
    return vote(texts)


def read(v, img):
    """-> {'build'|'research'|'train': (dang chay, tong) | None (thay icon, khong doc duoc so)}; icon khong thay
    thi khong co khoa."""
    out = {}
    for kind, tpl in ICONS.items():
        p = v.find(img, tpl, th=0.8, roi=COLUMN)
        if p:
            out[kind] = read_count(img, p[0], p[1])
    return out


def idle(q):
    """So cho ranh cua 1 hang cho (None = khong biet)."""
    return None if not q else q[1] - q[0]
