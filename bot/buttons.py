"""Do NUT theo MAU + CHU, khong can anh mau tung nut (chu du an 2026-11-21: "thuat toan nhan dien hinh anh dang qua
te. hinh anh trong kho co rat nhieu, nhung gan nhu khong giup cho viec thao tac thong minh hon").

Vi sao: moi nut "Nhan" / "Nhan toan bo" / "Den" la 1 anh mau rieng theo tung bang -> thieu 1 anh (vd "Nhan toan bo"
thuong chuong) la bot bo qua. Game dung cung 1 kieu nut cho moi bang:
  - nut NHAN (claim): chu nhat xanh ngoc, H ~84-90, S > 200   (do tren anh bang nhiem vu chuong / chinh)
  - nut DEN  (go)   : chu nhat xanh duong, H ~95-100, S > 200
=> tim khoi mau hinh chu nhat co kich thuoc nut, phan loai theo sac do, doc chu ben trong de xac nhan.
An toan: chu nut co dau hieu tra phi / kim cuong (Mua, Nap, "... ngay" tru "Nhan ngay", gia tien) -> bo (ADR-0008).
Ham thuan (anh -> danh sach nut), test offline tren anh that (ADR-0011).
"""
import re
from dataclasses import dataclass

import cv2
import numpy as np

from bot import ocr

CLAIM, GO = "claim", "go"
HUE_SPLIT = 92.5                 # < : xanh ngoc (Nhan); >= : xanh duong (Den)
DANGER = re.compile(r"\b(mua|nap|mo khoa|dung thu|thanh toan|vnd|usd|tang toc|ngay)\b|\$|\d+[.,]\d+\s*(d|vnd)")
SAFE_NGAY = re.compile(r"\bnhan ngay\b")
# chu nut NHAN (OCR 'eng' mat dau: 'nhan', 'nhen', 'nhan toan bo'). KHONG nhan theo mau mot minh: cung mau xanh ngoc con
# co 'Chieu mo', 'Dong', 'Bat dau lai' va nut MUA bang kim cuong ('@ 1000') - khao sat 350 anh that 2026-11-21
CLAIM_TXT = re.compile(r"\bnh\w{1,2}n\b|\bmi\w{1,2}n ph\w{1,2}\b")   # + "Mien phi" (chu du an 2026-11-22: co chu Mien phi thi nhan)


@dataclass(frozen=True)
class Button:
    x: int
    y: int
    w: int
    h: int
    kind: str
    hue: float
    text: str = ""


def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c)).lower()).strip()


def find(img, roi=None, min_w=60, max_w=320, min_h=28, max_h=90):
    """-> [Button] (chua doc chu), tren -> duoi."""
    ox, oy = 0, 0
    if roi:
        x, y, w, h = roi
        img, ox, oy = img[y:y + h, x:x + w], x, y
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hue = hsv[..., 0]
    m = ((hue >= 78) & (hue <= 104) & (hsv[..., 1] >= 180) & (hsv[..., 2] >= 70)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 9), np.uint8))   # lap chu trang trong nut
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if not (min_w <= w <= max_w and min_h <= h <= max_h and 1.4 <= w / h <= 7 and area >= 0.6 * w * h):
            continue
        hm = float(hue[lab == i].mean())
        out.append(Button(int(ox + x + w // 2), int(oy + y + h // 2), int(w), int(h),
                          CLAIM if hm < HUE_SPLIT else GO, round(hm, 1)))
    return sorted(out, key=lambda b: (b.y, b.x))


def read_text(img, b):
    pad = 4
    roi = (b.x - b.w // 2 + pad, b.y - b.h // 2 + pad, b.w - 2 * pad, b.h - 2 * pad)
    return _norm(ocr.text(img, roi, scale=3, psm=7, bright=170))


def is_danger(text):
    t = _norm(text)
    if SAFE_NGAY.search(t):
        t = SAFE_NGAY.sub("", t)
    return bool(DANGER.search(t))


def is_claim_text(text):
    t = _norm(text)
    return bool(CLAIM_TXT.search(t)) and not is_danger(t)


def claims(img, roi=None):
    """Nut NHAN an toan = mau xanh ngoc VA doc ra chu 'Nhan' VA khong co dau hieu tra phi. Khong doc duoc chu -> bo."""
    out = []
    for b in find(img, roi):
        if b.kind != CLAIM:
            continue
        t = read_text(img, b)
        if is_claim_text(t):
            out.append(Button(b.x, b.y, b.w, b.h, b.kind, b.hue, t))
    return out


def with_text(img, pattern, roi=None, kinds=(CLAIM, GO)):
    """Nut (xanh ngoc / xanh duong) co chu khop regex `pattern` (chu da bo dau, chu thuong), bo nut co dau hieu tra
    phi. -> [Button] tren -> duoi."""
    rx = re.compile(pattern)
    out = []
    for b in find(img, roi):
        if b.kind not in kinds:
            continue
        t = read_text(img, b)
        if rx.search(t) and not is_danger(t):
            out.append(Button(b.x, b.y, b.w, b.h, b.kind, b.hue, t))
    return out
