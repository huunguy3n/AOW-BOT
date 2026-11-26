"""P13i: CONG DUY NHAT ghi cap nha chinh (state.json `hq_level` + fact `hq_level`).

26/11: #2/#3 doc cap 7 luc 15:14/15:17, sau do man nang cap ghi thang 6 vao state (khong qua kiem tra nao, khong co
dong log). Luat (moi nguon doc deu di qua record):
  - chua biet cap cu: nhan; bang cap cu / +1: nhan (P13d);
  - nhay len > 1: can >= 2 lan doc co nhan trong cung 1 dot (P13d);
  - GIAM: khong bao gio tu 1 lan doc. Can >= 2 lan doc KHOP NHAU tu man chi tiet nha chinh (bang sau khi cham avatar co
    nhan "Xuong kien truc", hoac man nang cap co title_hq) - cung 1 dot, hoac 2 lan mo man cach nhau <= 24 gio (fact
    hq_low_pending); co lan doc >= cap cu chen vao -> dem lai. Ghi xuong thi log WARNING.
"""
import logging
import time

log = logging.getLogger("aow")
KEY = "hq_level"
PENDING = "hq_low_pending"          # {"lv", "n", "at", "src"}: cap thap hon da doc duoc, chua du 2 lan
PENDING_TTL_S = 24 * 3600


def judge_hq(prev, reads):
    """P13d-4 (live6c #5: ca luot HQ=4, cuoi luot doc 'cap 7' -> ghi 4->7 sai). Ham thuan. reads = [(cap, co_nhan), ...]
    (cac lan doc doc lap). -> cap duoc ghi | None (khong ghi, giu cap cu).
    - chua biet cap cu: nhan lan doc dau co so.
    - bang cap cu: ok. +1 cap: ok. Nhay > +1: chi nhan khi >= 2 lan doc trung nhau, deu co nhan.
    - GIAM (P13i): them dieu kien MOI lan doc trong dot deu ra dung cap do."""
    got = [(lv, lab) for lv, lab in reads if lv]
    if not got:
        return None
    for lv, _lab in got:
        if prev is None or lv in (prev, prev + 1):
            return lv
        if len([g for g in got if g[0] == lv and g[1]]) >= 2 and (lv > prev or all(g[0] == lv for g in got)):
            return lv
    return None


def note_hq(m, idx, prev, lv, targets=None):
    """P4: lich su cap nha chinh (fact 'hq_history' [[ts, cap], ...]) de do tieu chi 'moi farm len >= 1 cap / ngay'."""
    from aowbot.domain import hqplan as dom
    hist = m.fact(idx, "hq_history") or []
    if not hist or hist[-1][1] != lv:
        hist = ([*hist, [time.time(), lv]])[-60:]
        m.set_fact(idx, "hq_history", hist)
        t = dom.next_target(lv, targets or dom.DEFAULT_TARGETS)
        log.info("Nha chinh: cap %s -> %s (muc tieu ke tiep %s)", prev, lv, t or "da dat het")
    return hist


def stored(ctx):
    """Cap dang luu: lon nhat giua memory.db va state.json (hai noi lech nhau thi khong tin so thap) | None."""
    idx = ctx.dev.idx
    vals = []
    m = getattr(ctx, "mem", None)
    if m is not None:
        vals.append(m.fact(idx, KEY))
    inst = getattr(getattr(ctx, "store", None), "inst", None)
    if inst is not None:
        vals.append(inst(idx).get(KEY))
    nums = [int(v) for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return max(nums) if nums else None


def lowers(new, old):
    """Ham thuan: ghi `new` de len `old` la HA cap?"""
    return isinstance(new, (int, float)) and isinstance(old, (int, float)) and new < old


def _pending(m, idx, lv, now):
    """So lan da doc ra dung cap `lv` (thap hon) truoc day, con han."""
    p = m.fact(idx, PENDING) if m is not None else None
    if isinstance(p, dict) and p.get("lv") == lv and now - float(p.get("at") or 0) <= PENDING_TTL_S:
        return int(p.get("n") or 0)
    return 0


def _set_pending(m, idx, value):
    if m is not None and (value is not None or m.fact(idx, PENDING) is not None):
        m.set_fact(idx, PENDING, value)


def _commit(ctx, prev, lv):
    idx = ctx.dev.idx
    store, m = getattr(ctx, "store", None), getattr(ctx, "mem", None)
    if store is not None:
        store.update(idx, hq_level=lv)
    if m is not None:
        m.set_fact(idx, KEY, lv)
        note_hq(m, idx, prev, lv, (ctx.cfg.get("build") or {}).get("hq_targets"))


def record(ctx, reads, source):
    """Xet 1 dot doc cap nha chinh tu `source` va ghi neu hop le. reads = [(cap, co_nhan)], co_nhan = chac chan la man chi
    tiet nha chinh. -> cap vua duoc ghi (hoac xac nhan lai) | None (khong ghi, giu cap cu)."""
    got = [(int(lv), bool(lab)) for lv, lab in reads if lv]
    if not got:
        return None
    idx, m, now = ctx.dev.idx, getattr(ctx, "mem", None), time.time()
    prev = stored(ctx)
    if prev is not None and all(lv < prev for lv, _ in got):
        values = {lv for lv, _ in got}
        if len(values) != 1:
            _set_pending(m, idx, None)
            log.info("Nha chinh may %d: doc %s < cap dang luu %d, khong khop nhau - giu %d", idx, sorted(values), prev, prev)
            return None
        lv = values.pop()
        total = _pending(m, idx, lv, now) + sum(lab for _, lab in got)
        if total < 2:
            _set_pending(m, idx, {"lv": lv, "n": total, "at": now, "src": source} if total else None)
            log.info("Nha chinh may %d: doc cap %d < cap dang luu %d (%s) - CHUA ghi (%d/2 lan doc chi tiet khop)", idx,
                     lv, prev, source, total)
            return None
        _set_pending(m, idx, None)
        log.warning("Nha chinh may %d: HA cap %d -> %d (%d lan doc chi tiet khop nhau, nguon cuoi: %s)", idx, prev, lv,
                    total, source)
        _commit(ctx, prev, lv)
        return lv
    if prev is not None and any(lv >= prev for lv, _ in got):
        _set_pending(m, idx, None)      # co lan doc khong thap hon -> bo bang chung 'ha cap' cu
    lv = judge_hq(prev, got)
    if lv is not None:
        _commit(ctx, prev, lv)
    return lv
