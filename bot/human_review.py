"""Hoc tu thao tac TAY cua chu du an - qua DUYET (chu du an 2026-11-21: "cac giao dien ghi nhan tu thao tac cua toi
co dua vao cho may hoc khong?" -> truoc day khong: chi ghi exp kind='human' + anh logs/human/, khong hoc gi).

HumanWatch (bot/human.py) luu moi lan cham tay: <ngay>/<gio>-i<idx>-<buoc>-<n>_{before,after,mark}.png + events.jsonl.
Day la hang cho de chu du an duyet tren web (tab "Hoc & Agent"):
  - chi lay CHAM (tap) lam man DOI, tren man KHONG phai thanh pho / ban do (o do cham = vao tinh nang, khong phai
    dong man -> khong hoc duoc thanh "cham cho nay de thoat");
  - gom trung: cung man (dhash) + cung cho cham (o 40 px) -> 1 muc;
  - duyet = learn.teach(nhan, x, y) (mau kNN 'human': _learned_action cham dung cho do khi gap man rat giong);
    bo qua = danh dau da xem. KHONG tu hoc khi chua duyet (bai hoc bien the anh mau rac 2026-11-21).
"""
import json, os, threading

import cv2

from bot import learn, screens

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUMAN = os.path.join(BASE, "logs", "human")
STATE = os.path.join(BASE, "data", "learn", "human_review.json")
HOME = ("city", "world")          # cham tren 2 man nay = dieu huong, khong hoc
_lock = threading.Lock()


def _load():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"done": {}, "scr": {}}


def _save(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)


def _events(days=2):
    """-> [(ngay, su kien)] moi nhat truoc."""
    out = []
    for day in sorted(os.listdir(HUMAN), reverse=True)[:days] if os.path.isdir(HUMAN) else []:
        p = os.path.join(HUMAN, day, "events.jsonl")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    out.append((day, json.loads(line)))
                except ValueError:
                    pass
    out.sort(key=lambda x: -x[1].get("at", 0))
    return out


def pending(v, limit=24, scan=400, new_max=15):
    """Hang cho duyet. v = Vision (de doan loai man; ket qua doan duoc nho lai trong STATE)."""
    with _lock:
        st = _load()
        seen, items, fresh = set(), [], 0
        for day, ev in _events()[:scan]:
            if ev.get("type") != "tap" or not ev.get("changed") or not ev.get("before"):
                continue
            if not (0 <= ev.get("x", -1) < 540 and 0 <= ev.get("y", -1) < 960):
                continue        # HumanWatch doi toa do sai (gap 2026-11-21: 33,1168 / 675,181) -> khong day cho cham ao
            rel = f"{day}/{ev['before']}"
            if rel in st["done"]:
                continue
            scr = st["scr"].get(rel)
            if scr is None:
                if fresh >= new_max:       # nhan dien man ~0,1 s/anh -> moi lan tai trang chi lam them toi da new_max
                    continue
                fresh += 1
                img = cv2.imread(os.path.join(HUMAN, day, ev["before"]))
                if img is None:
                    continue
                scr = [screens.identify(img, v)[0], learn.dhash(img)]
                st["scr"][rel] = scr
            if scr[0] in HOME:
                continue
            key = (scr[1], ev["x"] // 40, ev["y"] // 40)
            if key in seen:
                continue
            seen.add(key)
            items.append({"file": rel, "mark": rel.replace("_before.png", "_mark.png"),
                          "after": f"{day}/{ev['after']}" if ev.get("after") else None,
                          "x": ev["x"], "y": ev["y"], "guess": scr[0], "step": ev.get("step"), "idx": ev.get("idx"),
                          "clock": ev.get("clock")})
            if len(items) >= limit:
                break
        if fresh:
            _save(st)
        return items


def mark_done(rel, how):
    """how: 'taught:<nhan>' | 'skip'."""
    with _lock:
        st = _load()
        st["done"][rel] = how
        _save(st)


def path_of(rel):
    """Duong dan anh 'truoc' cua 1 muc (chan '..')."""
    rel = (rel or "").replace("\\", "/")
    if ".." in rel.split("/") or not rel.endswith("_before.png"):
        return None
    p = os.path.normpath(os.path.join(HUMAN, rel))
    return p if p.startswith(os.path.normpath(HUMAN)) and os.path.isfile(p) else None


def exit_tap_ok(img, v, x, y, tol=60):
    """Hop thoai 'Roi tro choi?': cho cham PHAI la nut Huy (khong bao gio day bot bam 'Xac nhan' thoat game)."""
    p = v.find(img, "common/btn_cancel_exit")
    return bool(p) and abs(p[0] - x) <= tol and abs(p[1] - y) <= tol
