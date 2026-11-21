"""Giai doan B: "Toi dang o man nao?" + di toi man dich (thanh pho / ban do the gioi).

identify(img, v) va nav_action(img, v, target) la HAM THUAN (anh -> ket qua) -> test offline bang anh
logs/shots, tests/fixtures (tools/check_screens.py). Ctx.goto() thuc thi hanh dong va ghi nhat ky dieu huong.

Thu tu uu tien (man chong len nhau: popup tren thanh pho...):
  exit_dialog  hop thoai "Thoat game?"          -> Huy
  reward       bang nhan thuong                 -> cham dong
  popup        nut dong/xac nhan popup quen biet -> cham
  city / world nut chuyen ban do (goc duoi phai) -> xong, hoac cham de doi
  dialog       hoi thoai tan thu (Tiep)          -> cham
  panel        bang co nut quay lai              -> cham quay lai
  loading      man toi / gan nhu mot mau          -> doi
  unknown      khong nhan ra                     -> phim Back + luu mau vao logs/unknown/ de dan nhan
Chi dung anh mau DA CO trong templates/ (thieu -> coi nhu khong thay, dung quy uoc vision.py).
"""
import os, threading, time
import cv2, numpy as np

POPUPS = ["common/btn_confirm_hero", "common/btn_net_retry", "common/btn_rebuild", "common/btn_x", "common/btn_close",
          "common/btn_x_small", "common/btn_x_red", "common/tap_to_continue", "common/tap_to_close"]
BACKS = ["campaign/btn_done", "campaign/btn_done_lose", "common/btn_back", "common/btn_back2"]  # "Dong" truoc "<"
# bang co the dong bang phim Back (khong co nut quay lai rieng) - them tu anh "unknown" 2026-11-19
BACK_KEY = ["gather/btn_search_go"]
TOGGLE = {"city": "common/btn_to_world", "world": "common/btn_to_city"}  # o man X thi thay nut chuyen sang man kia
# Vung tim (x, y, w, h) cho tung anh mau - do tren 240 anh logs/ ngay 2026-11-19 (vi tri co dinh + bien 40px).
# Giam thoi gian identify tu ~0,4 s xuong vai chuc ms. Anh mau khong co trong ROI = tim ca man.
ROI = {"common/btn_to_world": (0, 860, 130, 100), "common/btn_to_city": (0, 860, 130, 100),
       "common/btn_close": (430, 0, 110, 960), "common/btn_x": (430, 0, 110, 330), "common/btn_x_small": (460, 0, 80, 90), "common/btn_x_red": (450, 0, 90, 90),
       "common/btn_back": (0, 0, 130, 960), "common/btn_back2": (0, 0, 130, 960),
       "tutorial/dialog_next": (440, 840, 100, 100), "common/msg_reward": (60, 170, 420, 130)}
UNKNOWN_DIR = os.path.join("logs", "unknown")
UNKNOWN_MAX = 300


def _find(v, img, n, th=None):
    return v.find(img, n, th=th, roi=ROI.get(n))


def _hit(v, img, names, th=None):
    for n in names:
        p = _find(v, img, n, th=th)
        if p:
            return n, p
    return None, None


def is_loading(img):
    """Man toi/gan nhu mot mau (dang tai, chuyen canh): do lech chuan anh xam rat thap hoac rat toi."""
    g = cv2.cvtColor(cv2.resize(img, (54, 96), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    return float(g.std()) < 6 or float(g.mean()) < 12


def identify(img, v):
    """-> (ten_man, chi_tiet) chi_tiet = (anh mau, (x, y, score)) neu co."""
    p = _find(v, img, "common/btn_cancel_exit")
    if p:
        return "exit_dialog", ("common/btn_cancel_exit", p)
    p = _find(v, img, "common/msg_reward", th=0.75)
    if p:
        return "reward", ("common/msg_reward", p)
    n, p = _hit(v, img, POPUPS)
    if n:
        return "popup", (n, p)
    for scr, n in TOGGLE.items():
        p = _find(v, img, n)
        if p:
            return scr, (n, p)
    p = _find(v, img, "tutorial/dialog_next", th=0.9)
    if p:
        return "dialog", ("tutorial/dialog_next", p)
    n, p = _hit(v, img, BACKS)
    if n:
        return "panel", (n, p)
    n, p = _hit(v, img, BACK_KEY)
    if n:
        return "panel_key", (n, p)
    if is_loading(img):
        return "loading", None
    return "unknown", None


_tl = threading.local()   # chi tiet identify cuoi (anh mau, diem) RIENG tung luong - Ctx.goto doc de ghi kinh nghiem


def last_detail():
    return getattr(_tl, "det", None)


def nav_action(img, v, target):
    """target: 'city' | 'world' | 'home' (mot trong hai). -> (man, hanh_dong, tham_so)
    hanh_dong: done | tap (x, y) | reward (x, y) | back | wait"""
    scr, det = identify(img, v)
    _tl.det = det
    if scr in ("city", "world"):
        if target in (scr, "home"):
            return scr, "done", None
        return scr, "tap", det[1][:2]  # cham nut chuyen ban do
    if scr in ("exit_dialog", "popup", "dialog", "panel"):
        return scr, "tap", det[1][:2]
    if scr == "panel_key":
        return scr, "back", None
    if scr == "reward":
        return scr, "reward", None
    if scr == "loading":
        return scr, "wait", None
    return scr, "back", None


def near_miss(img, v, names, lo=0.65):
    """Nut khop GAN nguong (lo <= diem < nguong) tot nhat trong names -> (ten, (x, y, diem)) hoac None.
    Dung cho man 'unknown' (giai doan F2): cham thu, man doi thi hoc bien the anh mau."""
    best = None
    for n in names:
        p = v.best(img, n, roi=ROI.get(n))
        if p and lo <= p[2] < v.th and (best is None or p[2] > best[1][2]):
            best = (n, p)
    return best


def dhash(img, n=8):
    g = cv2.cvtColor(cv2.resize(img, (n + 1, n), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return "".join("1" if b else "0" for b in bits)


def save_unknown(img, idx, tag=""):
    """Luu man la (bo trung theo dHash) de chu du an dan nhan / cat anh mau. Tra ve duong dan hoac None."""
    try:
        os.makedirs(UNKNOWN_DIR, exist_ok=True)
        h = hex(int(dhash(img), 2))[2:]
        if any(f.startswith(h) for f in os.listdir(UNKNOWN_DIR)):
            return None
        if len(os.listdir(UNKNOWN_DIR)) >= UNKNOWN_MAX:
            return None
        path = os.path.join(UNKNOWN_DIR, f"{h}-i{idx}-{time.strftime('%Y%m%d-%H%M%S')}{('-' + tag) if tag else ''}.png")
        cv2.imwrite(path, img)
        return path
    except Exception:
        return None


def same(a, b, th=2.0):
    """Hai anh gan nhu giong nhau (de phat hien 'cham ma man khong doi')."""
    ga = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (54, 96), interpolation=cv2.INTER_AREA).astype(np.int16)
    gb = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (54, 96), interpolation=cv2.INTER_AREA).astype(np.int16)
    return float(np.abs(ga - gb).mean()) < th
