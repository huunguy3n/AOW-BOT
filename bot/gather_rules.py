"""P3 (PM 2026-11-23): luat THUAN cho buoc thu thap (khong ctx, khong ADB) -> test offline.

1. Dung tich mo DAY theo (loai, cap): bang `gather.mine_caps` trong config (do tu log + chu du an) -> khong can doc
   so tren ban do khi tick "chi mo day". 111 anh gather_unread_* (21-22/11) deu la tru luong None (OCR tren nen cay
   sang), tai trong doc duoc ca 111 lan.
2. Mo cua CHINH MINH: hop thoai "Chu y! Co Chi huy truong khac dang hanh quan den diem tai nguyen nay, neu ban tiep
   tuc hanh quan, co the se xay ra chien tranh! muon tiep tuc xuat chinh? [Huy] [Tiep tuc]" hien khi CO DOI KHAC (ke ca
   quan doan khac cua minh) dang di toi mo. Log #1 22/11 16:44-16:48: metal cap 1 vua gui (di 1008 s) -> 51 s sau tim
   lai metal cap 1 = cung mo (cung 1008 s) -> hop thoai -> Huy. Mo day gan nhat chi "het day" khi doi toi noi, nen
   trong luc doi minh dang di, "Tim kiem" cung cap tra lai dung mo do.
3. Thong bao noi cua game (OCR dai giua man) khi thieu anh mau msg_* -> loai thong bao.
"""
import re

from aowbot.domain.blockers import normalize

# dung tich mo day mac dinh, index = cap - 1 (None = chua biet -> phai doc so). Nguon: memory.db #1 (mine_cap:*),
# log 19-22/11, chu du an 2026-11-22 (hop kim 7/8 = 62500 / 82500, kim loai 7 = 1040000).
DEFAULT_CAPS = {
    "metal": [40000, 80000, 160000, 320000, 560000, 800000, 1040000, 1320000],
    "food": [40000, 80000, 160000, 320000, 560000, 800000, 1040000, 1320000],
    "alloy": [None, None, 10000, 20000, 35000, 50000, 62500, 82500],
    "oil": [None, 20000, 40000, 80000, None, 200000, 260000, 330000],
}


def table_cap(caps, rtype, level):
    """Dung tich theo bang (config hoac mac dinh) | None."""
    row = (caps or DEFAULT_CAPS).get(rtype) or []
    if 1 <= level <= len(row) and row[level - 1]:
        return int(row[level - 1])
    return None


def choose_amount(read, cap, only_full=True, lo=0.9, hi=1.25):
    """-> (tru luong dung de so voi tai trong, nguon 'ocr'|'bang'|None).
    Chi mo day (only_full) + biet dung tich: OCR thieu / lech khoi [lo, hi] x dung tich (vd '40000' cho mo 1040000 -
    OCR rot chu so dau) -> dung DUNG TICH (lon nhat co the = an toan cho luat tai trong >= mo)."""
    if only_full and cap:
        if read is None or read < cap * lo or read > cap * hi:
            return cap, "bang"
        return read, "ocr"
    return (read, "ocr") if read else (None, None)


def own_target(dispatches, rtype, level, now, travel=None, tol_s=5, tol_pct=0.03, slack_s=60):
    """Doi cua minh dang DI (chua toi) toi mo (loai, cap) nay -> dict lan gui | None.
    travel=None: kiem truoc khi tim (moi doi cung loai/cap con dang di); co travel: phai trung thoi gian di
    (+-max(tol_s, tol_pct) - cung mo = cung khoang cach)."""
    for d in reversed(dispatches or []):
        if d.get("type") != rtype or d.get("level") != level:
            continue
        t, tr = d.get("t"), d.get("travel")
        if not t or not tr:
            continue
        if now > t + tr + slack_s:          # doi da toi mo -> mo het "day", tim kiem khong tra lai mo nay nua
            continue
        if travel is None or abs(travel - tr) <= max(tol_s, tr * tol_pct):
            return d
    return None


# thong bao noi (OCR 'eng' mat dau -> so khop sau normalize, cho phep sai vai chu)
_MSG_RULES = (
    ("contested", re.compile(r"chi huy tr\w{0,4}ng kh\w{1,3}c|tiep t\w{1,2}c xu\w{1,2}t ch\w{1,3}nh|xay ra chien tranh")),
    ("march_full", re.compile(r"(hanh quan|doi ngu|quan doan).{0,30}(toi da|da day|gioi han|het)|khong (con )?(du )?"
                              r"(doi|quan doan) (hanh quan )?(trong|ranh)")),
    ("no_troops", re.compile(r"khong (co|du) (binh|linh|quan)|het (binh|linh)|chua chon (binh|linh|quan)")),
    ("occupied", re.compile(r"(da|dang) (bi )?(chiem|chiem dong)|nguoi choi khac|dang (duoc )?thu thap")),
    ("not_found", re.compile(r"khong tim thay|khong co (diem|mo|tai nguyen)")),
    ("locked", re.compile(r"chua dat cap|tam thoi khong the thu thap")),
)


def classify_msg(text):
    """Chuoi OCR thong bao -> 'contested'|'march_full'|'no_troops'|'occupied'|'not_found'|'locked'|None."""
    s = normalize(text or "")
    for kind, pat in _MSG_RULES:
        if pat.search(s):
            return kind
    return None


def skip_until(kind, now, cfg):
    """Tam bo (loai, cap) qua cac lan ghe: mo bi chiem / tranh chap -> tim kiem tra lai dung mo do -> doi."""
    mins = {"occupied": cfg.get("occupied_skip_min", 30), "contested": cfg.get("contested_skip_min", 20),
            "not_found": cfg.get("notfound_skip_min", 30)}.get(kind)
    return now + mins * 60 if mins else None
