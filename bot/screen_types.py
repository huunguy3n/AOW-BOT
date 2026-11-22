"""Danh muc LOAI MAN mo rong duoc + MUC DICH cua cho cham (chu du an 2026-11-21: "trong he thong dang liet ke
it loai man hinh. Viec click khong chi don thuan la thoat, ma con co the la claim, thuc hien tien trinh nhiem vu").

- 10 loai GOC (learn.SCREEN_LABELS: city, world, popup, panel...) van la thu dieu huong (goto / kNN) dung.
- Loai CHI TIET do chu du an them tren web (vd "Tang cap tuong", "Danh sach kenh chat"), moi loai thuoc 1 loai goc
  -> mau kNN ghi theo loai GOC (dieu huong khong doi), ten chi tiet + muc dich ghi rieng (data/learn/taught.jsonl)
  cho che do lam theo mau / buoc moi dung sau.
- Muc dich cho cham: close (thoat/dong) | claim (nhan thuong) | progress (lam nhiem vu / tien trinh) | open (mo tinh
  nang). CHI 'close' duoc nap thanh 'cho cham de thoat' cho dieu huong (_learned_action).
- Co 'no_follow': bot KHONG lam theo thao tac tren loai man nay (vd chat - khong tu dong chat, CLAUDE.md).
"""
import json
import os
import re
import threading
import time
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(BASE, "data", "learn", "screen_types.json")
TAUGHT = os.path.join(BASE, "data", "learn", "taught.jsonl")
INTENTS = {"close": "Thoát / đóng", "claim": "Nhận thưởng", "progress": "Làm nhiệm vụ / tiến trình",
           "open": "Mở tính năng"}
BASE_VN = {"city": "Thành phố", "world": "Bản đồ thế giới", "popup": "Popup (có nút X)", "panel": "Bảng (nút quay lại)",
           "panel_key": "Bảng (đóng bằng Back)", "exit_dialog": "Hỏi thoát game", "reward": "Bảng nhận thưởng",
           "dialog": "Hội thoại", "loading": "Đang tải", "battle": "Trận đánh (không chạm)"}
_lock = threading.Lock()


def _load():
    try:
        with open(CATALOG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(d):
    os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
    tmp = CATALOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CATALOG)


def slug(vn):
    s = unicodedata.normalize("NFD", vn).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:40] or "man"


def catalog():
    """-> [{key, vn, parent, no_follow, note, base}] loai goc truoc, roi loai chi tiet."""
    out = [{"key": k, "vn": v, "parent": k, "no_follow": False, "note": "", "base": True} for k, v in BASE_VN.items()]
    out += [{"key": k, **v, "base": False} for k, v in sorted(_load().items(), key=lambda kv: kv[1]["vn"])]
    return out


def get(key):
    return next((t for t in catalog() if t["key"] == key), None)


def add(vn, parent, no_follow=False, note=""):
    """Them loai chi tiet (trung ten -> cap nhat). -> key"""
    vn = (vn or "").strip()
    if not vn or parent not in BASE_VN:
        raise ValueError("can ten va loai goc hop le")
    key = slug(vn)
    if key in BASE_VN:
        key += "_ct"
    with _lock:
        d = _load()
        d[key] = {"vn": vn, "parent": parent, "no_follow": bool(no_follow), "note": note.strip()}
        _save(d)
    return key


def record(file, type_key, intent, x=None, y=None, src="unknown"):
    """Ghi 1 lan day: man (file anh) -> loai chi tiet + muc dich cho cham."""
    if intent is not None and intent not in INTENTS:
        raise ValueError("muc dich khong hop le")
    os.makedirs(os.path.dirname(TAUGHT), exist_ok=True)
    with _lock, open(TAUGHT, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.time(), "file": file, "src": src, "type": type_key, "intent": intent,
                            "x": x, "y": y}, ensure_ascii=False) + "\n")


def taught():
    """-> {file: lan day moi nhat}"""
    out = {}
    try:
        with open(TAUGHT, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    out[r["file"]] = r
                except (ValueError, KeyError):
                    pass
    except OSError:
        pass
    return out


def teach(mem, v, img, file, type_key, intent=None, x=None, y=None, src="unknown"):
    """Day 1 man: loai (goc hoac chi tiet) + (tuy chon) cho cham va muc dich. -> None neu ok, chuoi loi neu khong.
    - mau kNN ghi theo loai GOC; cho cham chi nap cho dieu huong khi muc dich = 'close'
      (cham 'Tang cap' / 'Nhan' ma bi coi la 'cho thoat' thi goto se bam nham moi lan gap man nay);
    - hop thoai thoat game: cho cham 'close' phai la nut Huy;
    - anh -> tests/fixtures/taught/<goc>/ (hoi quy), lan day -> taught.jsonl."""
    import cv2
    from bot import human_review, learn
    t = get(type_key)
    if t is None:
        return "loai man khong hop le"
    if x is not None and intent is None:
        intent = "close"                  # cach day cu (chi co cho cham) = cho thoat
    if intent is not None and intent not in INTENTS:
        return "muc dich khong hop le"
    parent = t["parent"]
    if parent == "exit_dialog" and intent == "close" and x is not None and not human_review.exit_tap_ok(img, v, x, y):
        return "Hộp thoát game: chỗ chạm phải là nút Hủy"
    close = intent == "close" and x is not None
    learn.teach(mem, img, parent, x if close else None, y if close else None)
    record(file, t["key"], intent, x, y, src)
    dst = os.path.join(BASE, "tests", "fixtures", "taught", parent)
    os.makedirs(dst, exist_ok=True)
    cv2.imwrite(os.path.join(dst, os.path.basename(file)), img)
    return None
