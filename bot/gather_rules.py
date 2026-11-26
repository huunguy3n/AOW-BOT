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


def own_target(dispatches, rtype, level, now, travel=None, tol_s=5, tol_pct=0.03, slack_s=60, xy=None):
    """Doi cua minh dang DI (chua toi) toi mo (loai, cap) nay -> dict lan gui | None.
    travel=None: kiem truoc khi tim (moi doi cung loai/cap con dang di); co travel: phai trung thoi gian di
    (+-max(tol_s, tol_pct) - cung mo = cung khoang cach). P13g: biet toa do ca hai ben ma KHAC nhau -> mo khac."""
    for d in reversed(dispatches or []):
        if d.get("type") != rtype or d.get("level") != level:
            continue
        if xy and d.get("xy") and tuple(d["xy"]) != tuple(xy):
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


# ---------- P13g-3 (chu du an t92u 26/11/2026): khong bao gio gui 2 quan doan toi cung 1 mo ----------
# Toa do o thanh duoi ban do "# 32 X: 234 Y: 326" (tam ban do = mo vua tim) / duoi menu o "#32X:234Y:326"
_XY = re.compile(r"X\W{0,4}(\d{1,4})\W{0,4}Y\W{0,4}(\d{1,4})", re.I)
OWN_TILE_BLOCK_MIN = 480     # o vua gui quan toi: khong gui lai trong N phut (doi di + thu thap)


def parse_xy(text):
    """Chu OCR toa do -> (x, y) | None."""
    m = _XY.search(text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def same_mine(dispatches, xy, now, block_min=OWN_TILE_BLOCK_MIN):
    """Lan gui cua MINH toi dung o (x, y) nay trong block_min phut gan day (bat ke loai / cap / doi da toi hay
    chua) -> dict lan gui | None. Khong doc duoc toa do -> None (con luat thoi gian di own_target)."""
    if not xy:
        return None
    for d in reversed(dispatches or []):
        if d.get("xy") and tuple(d["xy"]) == tuple(xy) and d.get("t") and now - d["t"] <= block_min * 60:
            return d
    return None


# ---------- P7-1 (live #1 2026-11-24): mo cap 1 'toobig' ----------
def bigger_mine(reads, caps, rtype, level):
    """Cac so OCR duoc duoi mo: co so TRUNG DUNG dung tich mo day cua 1 cap CAO HON cap dang tim (vd doc 560000 khi
    tim cap 2) -> mo tren man that su lon hon -> tra so do (lon nhat) de ap luat tai trong; khong -> None.
    P13g (log #1 26/11 07:30: doc '560000' bi loai 'khong hop ly' roi dung dung tich bang 160000)."""
    row = (caps or DEFAULT_CAPS).get(rtype) or []
    higher = {int(c) for c in row[level:] if c}
    here = table_cap(caps, rtype, level) or 0
    hit = [v for v in reads or [] if v in higher and v > here]
    return max(hit) if hit else None


def too_big_levels(caps, rtype, load, lv, min_lv):
    """Mo (rtype, lv) qua tai voi quan doan dang chon (tai trong `load`) -> cac cap con lai (< lv) CUNG qua tai theo bang
    (dung tich tang theo cap) -> bo luon, khong mo ban do tung cap. Tra ve danh sach cap can bo (khong gom lv)."""
    if not load:
        return []
    out = []
    for x in range(lv - 1, min_lv - 1, -1):
        cap = table_cap(caps, rtype, x)
        if cap and cap > load:
            out.append(x)
    return out
