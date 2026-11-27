"""LAM THEO MAU (giai doan 2 cua che do hoc mau, chu du an 2026-11-21: "toi se lam mau thao tac o #3. Hoc tu do
va lam theo"; chon: phan ung theo man hinh, tin mau + chan nut nguy hiem).

Moi lan cham MAU (logs/human, HumanWatch) -> 1 'demo': dac trung ca man TRUOC khi cham (learn.feat) + manh anh
72x72 quanh cho cham (cai bieu tuong / nut chu du an bam) + toa do.

decide(anh, demos) - HAM THUAN (ADR-0011, test offline bang tools/imitate_eval.py):
  1. man hien tai giong man cua demo (cosine >= th_scr) -> ung vien;
  2. manh anh cua demo VAN CON gan cho cu (template matching >= th_crop trong ban kinh radius) -> cham vao do.
     => dieu kien 'con viec': icon con cham do thi khop, cham xong cham do mat -> khong khop -> khong lap lai;
  3. nhieu ung vien -> diem = sim_man x khop_manh, cao nhat.
  Khong ung vien nao du tin -> None (bot dung lai, khong doan).
An toan (is_danger): chu quanh cho cham co 'Mua', 'Nap', '... ngay' (tru 'Nhan ngay'), 'Mo khoa', 'Dung thu',
gia tien -> KHONG cham, du chu du an tung bam (chinh sach kim cuong, ADR-0008).
"""
import json
import logging
import os
import re

import cv2
import numpy as np

from bot import learn

log = logging.getLogger("aow")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUMAN = os.path.join(BASE, "logs", "human")
HALF = 36                                   # manh anh 72x72 quanh cho cham
GOOD = ("changed", "dot_gone", "reward", "local")   # cham mau co tac dung (bo 'none' = cham hut)
CHAIN_S = 10                                # 2 lan cham mau cach <= N giay = cung 1 chuoi thao tac
W, H = 540, 960


def crop(img, x, y, half=HALF):
    x0, y0 = max(0, x - half), max(0, y - half)
    c = img[y0:y + half, x0:x + half]
    return c if c.shape[:2] == (2 * half, 2 * half) else None


def make_demo(img, ev, key):
    c = crop(img, ev["x"], ev["y"])
    if c is None:
        return None
    return {"key": key, "t": ev.get("at", 0), "x": ev["x"], "y": ev["y"], "feat": learn.feat(img),
            "crop": cv2.cvtColor(c, cv2.COLOR_BGR2GRAY), "outcome": ev.get("outcome")}


def load_demos(idx, root=HUMAN, since=0.0):
    """Doc moi lan CHAM co tac dung cua may idx (None = moi may) tu logs/human -> danh sach demo."""
    out = []
    for day in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        p = os.path.join(root, day, "events.jsonl")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in lines:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ((idx is not None and ev.get("idx") != idx) or ev.get("type") != "tap" or ev.get("outcome") not in GOOD
                    or not ev.get("before") or ev.get("at", 0) < since
                    or not (0 <= ev.get("x", -1) < W and 0 <= ev.get("y", -1) < H)):
                continue
            img = cv2.imread(os.path.join(root, day, ev["before"]))
            if img is None:
                continue
            d = make_demo(img, ev, f"{day}/{ev['before']}")
            if d:
                out.append(d)
    out.sort(key=lambda d: d["t"])
    # nhan chu du an day tren web (loai man chi tiet + muc dich): man 'khong lam theo' (vd chat) -> bo mau
    from bot import screen_types
    tg, nof = screen_types.taught(), {t["key"] for t in screen_types.catalog() if t["no_follow"]}
    for d in out:
        r = tg.get(d["key"])
        if r:
            d["type"], d["intent"] = r.get("type"), r.get("intent")
    out = [d for d in out if d.get("type") not in nof]
    for a, b in zip(out, out[1:]):        # chuoi thao tac: b lam NGAY sau a (<= CHAIN_S giay) -> b.prev = a
        if b["t"] - a["t"] <= CHAIN_S:
            b["prev"] = a
    return out


def same_action(a, b, th=0.95, px=40):
    """2 thao tac 'giong nhau': cung man (cosine) + cung cho cham."""
    return (a is not None and b is not None and float(a["feat"] @ b["feat"]) >= th
            and abs(a["x"] - b["x"]) <= px and abs(a["y"] - b["y"]) <= px)


class Index:
    """Demo da nap san thanh ma tran de tim nhanh. stop = dac trung cac man chu du an danh dau 'bot khong lam theo'
    (vd danh sach kenh chat): gap man giong -> khong cham gi, chi thoat ve."""

    def __init__(self, demos, stop=None):
        self.demos = demos
        self.F = np.stack([d["feat"] for d in demos]) if demos else np.zeros((0, learn.FEAT_DIM * 2), np.float32)
        self.stop = np.stack(stop) if stop else None

    def __len__(self):
        return len(self.demos)


_shared = {"index": None, "at": 0.0, "loading": False}


def shared_index(max_age_h=6):
    """M1-3: Index demo cua MOI may (dung chung cho man la o moi may). Nap o luong nen (~3000 anh, vai chuc giay):
    lan dau / het han -> bat dau nap va tra Index cu (hoac None); khong bao gio chan buoc dang chay."""
    import threading
    import time
    now = time.time()
    if not _shared["loading"] and (_shared["index"] is None or now - _shared["at"] > max_age_h * 3600):
        _shared["loading"] = True

        def load():
            try:
                _shared["index"] = Index(load_demos(None), stop_feats())
                _shared["at"] = time.time()
                log.info("Lam theo (man la): nap %d thao tac mau cua moi may", len(_shared["index"]))
            except Exception as e:
                log.warning("Lam theo (man la): khong nap duoc mau: %s", e)
                _shared["at"] = time.time()
            finally:
                _shared["loading"] = False
        threading.Thread(target=load, name="imitate-load", daemon=True).start()
    return _shared["index"]


def unknown_action(img, index, blocked=(), th_scr=0.95, th_crop=0.9):
    """M1-3 (ham thuan): man 'unknown' -> {'x','y','key',...} theo thao tac tay giong nhat cua moi may, hoac None.
    Nguong chat hon follow() (man la it ngu canh). Man 'khong lam theo' (chat...) -> None."""
    if index is None or not len(index):
        return None
    if index.stop is not None and float((index.stop @ learn.feat(img)).max()) >= STOP_SIM:
        return None
    return decide(img, index, blocked=blocked, th_scr=th_scr, th_crop=th_crop)


def stop_feats():
    """Dac trung anh cac man da day thuoc loai 'khong lam theo' (anh luu o tests/fixtures/taught/<goc>/)."""
    from bot import screen_types
    types = {t["key"]: t for t in screen_types.catalog()}
    out = []
    for r in screen_types.taught().values():
        t = types.get(r.get("type"))
        if t and t["no_follow"]:
            img = cv2.imread(os.path.join(BASE, "tests", "fixtures", "taught", t["parent"], os.path.basename(r["file"])))
            if img is not None:
                out.append(learn.feat(img))
    return out


def decide(img, index, blocked=(), last=None, th_scr=0.9, th_crop=0.85, radius=90, top=40, exclude=None):
    """-> {'x','y','key','sim','match','score','chain'} hoac None. blocked: tap hop key demo khong duoc dung (vd vua
    cham ma man khong doi). last = demo bot vua lam (ngu canh chuoi): ung vien ma chu du an tung lam NGAY SAU mot
    thao tac giong 'last' duoc uu tien truoc moi ung vien khac. exclude(demo) -> True: bo demo (danh gia bo-ra)."""
    if not len(index):
        return None
    f = learn.feat(img)
    sims = index.F @ f
    order = np.argsort(-sims)[:top]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    best = None
    for i in order:
        s = float(sims[i])
        if s < th_scr:
            break
        d = index.demos[i]
        if d["key"] in blocked or (exclude and exclude(d)):
            continue
        x0, y0 = max(0, d["x"] - HALF - radius), max(0, d["y"] - HALF - radius)
        win = g[y0:d["y"] + HALF + radius, x0:d["x"] + HALF + radius]
        if win.shape[0] < d["crop"].shape[0] or win.shape[1] < d["crop"].shape[1]:
            continue
        r = cv2.matchTemplate(win, d["crop"], cv2.TM_CCOEFF_NORMED)
        _, m, _, loc = cv2.minMaxLoc(r)
        if m < th_crop:
            continue
        sc = s * m
        chain = bool(last is not None and same_action(d.get("prev"), last))
        if best is None or (chain, sc) > (best["chain"], best["score"]):
            best = {"x": x0 + loc[0] + HALF, "y": y0 + loc[1] + HALF, "key": d["key"], "sim": round(s, 3),
                    "match": round(float(m), 3), "score": round(sc, 4), "chain": chain, "demo": d}
    return best


DANGER = re.compile(r"\b(mua|nap|mo khoa|dung thu|thanh toan|vnd|usd|goi uu dai)\b|\$\s*\d|\d+[.,]\d+\s*(d|vnd|\$)")


def norm(s):
    """Bo dau tieng Viet + thuong (Tesseract chi goi 'eng' -> chu thuong mat dau san, van chuan hoa cho chac)."""
    import unicodedata
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn").lower()).strip()


def is_danger(text):
    """Chu tren / quanh nut -> True neu la nut ton tien / kim cuong.
    'ngay' (Xay dung / Tang cap / Tang toc / Huan luyen ... ngay) = tieu kim cuong, TRU khi:
      - nut ghi 'Mien phi' (moc mien phi: so kim cuong = 0 -> dung luat, chu du an 2026-11-21: 5 lan bam mau
        'Xay dung ngay / Tang cap ngay' deu la 'Mien phi');
      - 'Nhan ngay' (nhan thuong) hoac 'hang ngay' (Nhiem vu hang ngay).
    Doc ra so kim cuong / khong doc duoc dong duoi -> van chan (OCR hay meo dong tu -> chan rong)."""
    t = norm(text)
    if DANGER.search(t):
        return True
    if not re.search(r"\bngay\b", t) or re.search(r"\b(nhan|hang) ngay\b", t):
        return False
    return not FREE.search(t)


FREE = re.compile(r"\bmien ph")       # 'Mien phi' duoi bieu tuong kim cuong (OCR doi khi cat chu 'i')


def text_near(img, x, y):
    """OCR khoi chu quanh cho cham: nut 2 dong (vd 'Xay dung ngay' / kim cuong 'Mien phi') rong ~200, cao ~70 px."""
    from bot import ocr
    if ocr._ok is None:                    # chua khoi tao (chay ngoai main.py) -> duong dan mac dinh
        ocr.init("C:/Program Files/Tesseract-OCR/tesseract.exe")
    x0, y0 = max(0, x - 110), max(0, y - 40)
    return ocr.text(img, (x0, y0, min(W - x0, 220), min(H - y0, 80)), psm=6)


# ---------------------------------------------------------------- chinh sach + vong lam theo tren may that
LOOSE = ("popup", "reward", "dialog", "exit_dialog")
STOP_SIM = 0.95                                        # giong man 'khong lam theo' tu muc nay -> dung   # man it lua chon: tin hang xom gan nhat (do offline 83 %)


def choose(img, index, scr, last=None, blocked=(), strict=(0.98, 0.97), **kw):
    """decide() + luat theo loai man (do 2026-11-21 tren 368 mau #3, bo-ra +-60 s):
    popup/thuong/hoi thoai -> lay hang xom tot nhat; bang chuc nang / thanh pho / ban do (nhieu viec co the lam,
    doan chi dung ~36 %) -> CHI cham khi co ngu canh chuoi + man rat giong (chinh xac ~84 %)."""
    if index.stop is not None and float((index.stop @ learn.feat(img)).max()) >= STOP_SIM:
        return None                      # man 'bot khong lam theo' (vd chat) -> khong cham, follow() se thoat ve
    r = decide(img, index, blocked=blocked, last=last, **kw)
    if r and scr not in LOOSE and not (r["chain"] and r["sim"] >= strict[0] and r["match"] >= strict[1]):
        return None
    return r


def follow(ctx, index, cfg, check, update=None):
    """Lam theo mau tren may that. Dung khi: khong con thao tac du tin (o thanh pho/ban do), cham 3 lan lien khong
    an, het follow.max_actions / follow.max_min, hoac bam Dung. -> {'done','danger','miss','why'}"""
    import time
    from bot import screens
    f = cfg.get("follow") or {}
    max_n, t_end = f.get("max_actions", 80), time.time() + f.get("max_min", 30) * 60
    blocked, uses = set(), {}
    last, miss, done, danger, why = None, 0, 0, 0, "het viec du tin"
    while True:
        check()
        if done >= max_n or time.time() > t_end:
            why = "het luot / het gio"
            break
        img = ctx.shot()
        scr = screens.identify(img, ctx.v)[0]
        r = choose(img, index, scr, last=last, blocked=blocked)
        if r is None:
            if scr in ("city", "world"):
                break
            ctx.ensure_city()            # man khong co mau du tin -> ve thanh pho bang dieu huong san co
            last = None
            continue
        if is_danger(text_near(img, r["x"], r["y"])):
            danger += 1
            blocked.add(r["key"])
            log.warning("Lam theo: BO cham %d,%d (%s) - nut ton tien / kim cuong", r["x"], r["y"], r["key"])
            continue
        uses[r["key"]] = uses.get(r["key"], 0) + 1
        if uses[r["key"]] > f.get("max_repeat", 4):      # chong lap vong
            blocked.add(r["key"])
            continue
        if update:
            update(f"làm theo: {done} thao tác")
        log.info("Lam theo: cham %d,%d (man %s, giong %.3f, khop %.3f%s)", r["x"], r["y"], scr, r["sim"], r["match"],
                 ", theo chuoi" if r["chain"] else "")
        ctx.tap(r["x"], r["y"], wait=f.get("wait_s", 1.2), tpl="imitate")
        if screens.same(img, ctx.shot()):
            miss += 1
            blocked.add(r["key"])
            if miss >= 3:
                why = "3 lan cham khong an"
                break
            continue
        miss, last, done = 0, r["demo"], done + 1
    log.info("Lam theo: xong %d thao tac, bo %d nut nguy hiem (%s)", done, danger, why)
    return {"done": done, "danger": danger, "miss": miss, "why": why}
