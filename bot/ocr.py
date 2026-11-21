"""Doc so/chu tren man hinh bang Tesseract (man 540x960).

Chi co goi ngon ngu 'eng' -> chu tieng Viet doc ra khong dau ("Dang hinh quan"), nen trang thai
hanh quan duoc phan loai theo tu khoa gan dung.
"""
import os, re, logging
import cv2

from bot import perf

log = logging.getLogger("aow")
_ok = None

# Vung tren thanh tren cung (x, y, w, h) - giong nhau o thanh pho va ban do the gioi
TOPBAR = {
    "metal": (30, 3, 62, 22),
    "food": (118, 3, 62, 22),
    "stamina": (388, 3, 45, 22),   # the luc (tia set xanh)
    "gold": (478, 3, 60, 22),
    "gems": (430, 29, 64, 24),     # kim cuong
    "power": (240, 28, 82, 26),    # luc chien (canh icon to nha)
}
# Khung "Hanh quan x/y" goc trai tren (chi hien khi co doi dang di)
MARCH_STATUS = (50, 166, 120, 18)   # dong 1: trang thai
MARCH_TIMER = (52, 186, 70, 16)     # dong 1: dong ho dem nguoc
MARCH_ROW_H = 50                    # khoang cach giua cac dong (CHUA kiem chung voi >1 doi)


def init(cmd):
    global _ok
    try:
        import pytesseract
        if cmd and os.path.exists(cmd):
            pytesseract.pytesseract.tesseract_cmd = cmd
        pytesseract.get_tesseract_version()
        _ok = True
    except Exception as e:
        log.warning("Khong dung duoc Tesseract: %s", e)
        _ok = False
    return _ok


def text(img, roi, whitelist=None, scale=3, psm=7, bright=None):
    """bright=N: chi giu diem anh sang hon N (chu trang tren nen mau/thanh tien do)."""
    if not _ok:
        return ""
    import pytesseract
    x, y, w, h = roi
    g = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if bright:
        b = 255 - cv2.threshold(g, bright, 255, cv2.THRESH_BINARY)[1]  # chu den, nen trang
    else:
        _, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if b.mean() < 127:  # chu sang tren nen toi -> dao thanh chu den nen trang
            b = 255 - b
    cfg = f"--psm {psm}" + (f" -c tessedit_char_whitelist={whitelist}" if whitelist else "")
    try:
        with perf.measure("ocr"):            # 1 tien trinh tesseract / lan goi
            return pytesseract.image_to_string(b, config=cfg).strip()
    except Exception as e:
        log.debug("ocr loi: %s", e)
        return ""


def amount(s):
    """'201.7K' -> 201700, '1.2M' -> 1200000, '80000' -> 80000; None neu khong doc duoc."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*([KMB]?)", (s or "").replace(",", ""))
    if not m:
        return None
    v = float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[m.group(2)]
    return int(v)


def seconds(s):
    """'00:18:50' -> 1130; '0:18:50' cung duoc; None neu khong doc duoc."""
    m = re.search(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})", s or "")
    if not m:
        return None
    h, mi, se = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
    return h * 3600 + mi * 60 + se


def label_number(img, roi, gap=4):
    """So mau xam sang canh 1 icon mau (vd '80000' duoi mo). Chi giu diem sang it bao hoa (bo icon),
    lay cum diem ben PHAI nhat (chu so cach nhau < gap px), cat sat roi OCR."""
    import numpy as np
    x, y, w, h = roi
    hsv = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2HSV)
    mask = (hsv[..., 2] > 150) & (hsv[..., 1] < 60)
    cols = np.where(mask.sum(0) > 0)[0]
    if not len(cols):
        return None
    end = start = cols[-1]
    for c in cols[::-1][1:]:
        if start - c > gap:
            break
        start = c
    x0, x1 = max(0, start - 3), min(w, end + 4)
    return amount(text(img, (x + x0, y, x1 - x0, h), "0123456789", scale=4))


# TK cap cao (#1, 2026-11-21): thanh tren co 6 o (kim loai, thuc pham, DAU, HOP KIM, the luc "363,000", vang);
# farm chi 4 o -> o thu 3 (x 205-275) trong. Luc chien 8 chu so (78.696.032) -> o rong hon.
TOPBAR_MAIN = {
    "metal": (30, 3, 62, 22), "food": (118, 3, 62, 22), "oil": (205, 3, 70, 22), "alloy": (298, 3, 52, 22),
    "stamina": (385, 3, 65, 22), "gold": (470, 3, 68, 22), "gems": (430, 29, 64, 24), "power": (225, 28, 100, 26),
}


def topbar(img):
    out = {}
    six = amount(text(img, TOPBAR_MAIN["oil"], "0123456789.,KMB")) is not None
    for k, roi in (TOPBAR_MAIN if six else TOPBAR).items():
        out[k] = amount(text(img, roi, "0123456789.,KMB"))
    if not six:   # farm: thu o luc chien rong hon neu o hep doc ra it chu so hon
        wide = amount(text(img, TOPBAR_MAIN["power"], "0123456789.,KMB"))
        if wide and out["power"] is None:          # o rong doc nham icon thanh '1' o farm -> chi khi o hep hong
            out["power"] = wide
    return out


def march_state(s):
    t = (s or "").lower()
    if "tro " in t or "tro" in t.split() or " ve " in t + " ":
        return "returning"
    if "thu" in t or "thap" in t or "thd" in t:
        return "gathering"
    if "hanh" in t or "hinh" in t or "quan" in t:
        return "marching"
    return "unknown"


def marches(img, count):
    """Doc trang thai + dong ho cua `count` doi dau tien trong khung Hanh quan."""
    out = []
    for i in range(count):
        dy = i * MARCH_ROW_H
        sx, sy, sw, sh = MARCH_STATUS
        tx, ty, tw, th = MARCH_TIMER
        # chu tren thanh tien do mau xanh (tro ve/thu thap) can nguong sang; hanh quan thi Otsu
        st = text(img, (sx, sy + dy, sw, sh), bright=170) + " | " + text(img, (sx, sy + dy, sw, sh))
        roi = (tx, ty + dy, tw, th)
        tm = seconds(text(img, roi, "0123456789:", bright=150)) or seconds(text(img, roi, "0123456789:"))
        state = march_state(st)
        if state == "unknown" and tm:
            state = "marching"
        out.append({"state": state, "remaining": tm, "raw": st})
    return out
