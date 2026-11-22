"""Quan sat cuoi moi luot: tai nguyen thanh tren + danh sach hanh quan -> ghi vao state cho web.

Thoi gian tuyet doi (epoch) de web tu dem nguoc:
  marching  : arrive_at   (toi mo), gather_done/return_at chua biet
  gathering : gather_done (thu thap xong), return_at = gather_done + thoi gian di (uoc tinh)
  returning : return_at
"""
import re, time, logging
import cv2, numpy as np
from bot import ocr, queues
from aowbot.domain import marches

log = logging.getLogger("aow")


def remember(mem, idx, info, now):
    """Ghi tri nho (A1): moi doi dang di -> timer march:<i> = luc doi ve thanh (ranh lai).
    Doi dang thu thap ma chua biet thoi gian di -> lay luc thu thap xong (conf thap, som hon thuc te = an toan).
    Doi dang toi mo -> chua biet bao gio ve: khong dat timer (lich dung tran max_gap)."""
    mem.clear_timers(idx, "march:")
    mem.clear_timers(idx, "arrive:")
    for t in marches.timers_from_rows(info.get("marches") or []):   # luat o aowbot.domain.marches
        mem.set_timer(idx, f"{t.kind}:{t.index}", t.due_at, t.source, t.confidence)
    for k in ("march_total", "march_used", "resources", "last_travel"):
        if info.get(k) is not None:
            mem.set_fact(idx, k, info[k])
    mem.set_fact(idx, "observed_at", now)


HQ_ROI = (160, 758, 180, 22)  # dong "Cap Xuong kien truc: N" trong man Thong tin Chi huy truong (cham avatar)


def parse_hq(text):
    # OCR hay doc sai chu ("truc" -> "tric") -> chi dua vao so sau dau ':' (lan loi #0 2026-11-19 08:43)
    m = re.search(r"[:;]\s*(\d{1,2})\b", text or "") or re.search(r"tr\S{0,2}c\s*(\d{1,2})\b", text or "", re.I)
    return int(m.group(1)) if m else None


HQ_DIGIT_ROI = (280, 758, 60, 22)  # phan "truc: N" - doc rieng chu so khi dong day du doc hong


def ocr_hq(img):
    lv = parse_hq(ocr.text(img, HQ_ROI))
    if not lv:
        d = ocr.text(img, HQ_DIGIT_ROI, "0123456789").strip()
        lv = int(d) if d.isdigit() and 0 < int(d) <= 40 else None
    return lv


def read_hq(ctx, every_h=6):
    """Cap nha chinh (Xuong kien truc) cho gather/research/lich. Cham avatar goc trai tren -> OCR -> quay lai.
    Chi doc khi chua biet hoac da cu hon every_h gio (ton ~5 s)."""
    m = getattr(ctx, "mem", None)
    idx = ctx.dev.idx
    st = ctx.store.inst(idx) if getattr(ctx, "store", None) else {}
    if ctx.cfg.get("modules", {}).get("tutorial") and not st.get("tutorial_done"):
        return None  # dang tan thu: huong dan che man hinh, cham avatar khong mo duoc (#2 2026-11-19 09:17)
    if m:
        r = m.query("SELECT seen_at FROM facts WHERE inst=? AND key='hq_level'", (idx,))
        if r and r[0][0] and time.time() - r[0][0] < every_h * 3600:
            return m.fact(idx, "hq_level")
    ctx.ensure_city()
    ctx.tap(38, 38, wait=1.8)
    lv = ocr_hq(ctx.shot())
    if not lv:  # bang chua hien xong -> doc lai 1 lan, hong thi luu anh de xem (lan dau #0 2026-11-19 08:08)
        time.sleep(1.5)
        lv = ocr_hq(ctx.shot())
        if not lv:
            ctx.save_debug("hq_unread")
    ctx.ensure_city()
    if lv:
        log.info("Nha chinh (Xuong kien truc) cap %d", lv)
        if getattr(ctx, "store", None):
            ctx.store.update(idx, hq_level=lv)
        if m:
            m.set_fact(idx, "hq_level", lv)
    else:
        log.info("Khong doc duoc cap nha chinh")
    return lv


def read_builders(v, img):
    """Icon bua + co le goc trai tren thanh pho, so "dang xay/tong" (vd 1/2). -> (dang_xay, tong) | None.
    Farm hien x/2 nhung chi dung 1 tho (o thu 2 phai thue); TK chinh #1 co 2 (chu du an 2026-11-21)."""
    p = v.find(img, "build/icon_builder", th=0.8, roi=(0, 90, 120, 320))
    if not p:
        return None
    m = re.search(r"(\d)\s*/\s*(\d)", ocr.text(img, (p[0] + 31, p[1] - 14, 32, 22), "0123456789/", scale=4) or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _link_dispatches(marches, disp, now):
    """Gan moi doi doc duoc voi lan gui tuong ung (loai/cap/tru luong mo, luc xuat phat) de web ve timeline.
    Doi dang di: lan gui co (t + travel) gan arrive_at nhat. Con lai: lan gui moi nhat chua gan, xep theo thu tu."""
    free = sorted([d for d in disp if now - d.get("t", 0) < 86400], key=lambda d: d["t"])
    for m in marches:
        if not free:
            break
        if m.get("arrive_at"):
            d = min(free, key=lambda d: abs(d["t"] + (d.get("travel") or 0) - m["arrive_at"]))
        else:
            d = free[0]
        free.remove(d)
        m.update(depart_at=d["t"], type=d.get("type"), level=d.get("level"), amount=d.get("amount"),
                 load=d.get("load"), travel=d.get("travel"))
        if m["state"] == "marching" and d.get("travel") and not m.get("arrive_at"):
            m["arrive_at"] = d["t"] + d["travel"]


def note_heal(ctx, cimg):
    """P1 (stepgate): bong bong chua tri tren benh vien co hien khong -> fact heal_bubble (heal chi chay khi thay,
    hoac vua co tran). Thieu anh mau -> khong ghi (heal van chay nhu cu)."""
    m = getattr(ctx, "mem", None)
    if m is None or not ctx.v.has("build/heal_bubble"):
        return
    try:
        m.set_fact(ctx.dev.idx, "heal_bubble", bool(ctx.v.find(cimg, "build/heal_bubble", th=0.8, roi=(0, 110, 540, 700))))
    except Exception as e:
        log.debug("heal_bubble: %s", e)


def known_totals(ctx):
    """P2: tong cua tung hang cho tu lan doc truoc (fact queue_<loai> = [dang chay, tong]) -> lop cham do cua
    queues.read dung khi khong doc duoc so."""
    m = getattr(ctx, "mem", None)
    out = {}
    if m is None:
        return out
    for k in queues.ICONS:
        try:
            v = m.fact(ctx.dev.idx, f"queue_{k}")
            if v and len(v) == 2 and int(v[1]) >= 1:
                out[k] = int(v[1])
        except Exception:
            pass
    return out


def run(ctx):
    if ctx.cfg.get("observe", {}).get("read_hq", True):
        try:
            read_hq(ctx)
        except Exception as e:  # khong de doc cap nha chinh lam hong quan sat
            log.warning("Doc cap nha chinh loi: %s", e)
    ctx.ensure_city()
    cimg = ctx.shot()
    qs = queues.read(ctx.v, cimg, known_totals(ctx))   # Q0/P2: tho xay / nghien cuu / huan luyen tu cot icon trai
    b = qs.get("build") or read_builders(ctx.v, cimg)
    if qs:
        log.info("Hang cho: %s", ", ".join(f"{k} {v[0]}/{v[1]}" if v else f"{k} ?" for k, v in qs.items()))
        if getattr(ctx, "store", None):
            ctx.store.update(ctx.dev.idx, queues={k: list(v) if v else None for k, v in qs.items()},
                             queues_at=time.time())
        if getattr(ctx, "mem", None):
            ctx.mem.log_queues(ctx.dev.idx, time.time(), qs)
            for k, v in qs.items():
                if v:
                    ctx.mem.set_fact(ctx.dev.idx, f"queue_{k}", list(v))
    if b and getattr(ctx, "mem", None):
        ctx.mem.set_fact(ctx.dev.idx, "builders_busy", b[0])
        log.info("Tho xay: %d/%d dang xay (dung toi da %d)", b[0], b[1], ctx.cfg.get("build", {}).get("max_builders", 1))
    note_heal(ctx, cimg)
    base_state(ctx, cimg, b)
    world = ctx.world_ready() if hasattr(ctx, "world_ready") else True
    if world:
        ctx.ensure_world()
        time.sleep(1.0)
    else:
        ctx.ensure_city()           # ban do the gioi chua mo: chi doc tai nguyen o thanh pho, khong doc hanh quan
    img = ctx.shot()
    res = ocr.topbar(img)
    now = time.time()
    used_total = ctx.read_marches() if world else None
    reserve = 0
    try:
        from bot.modules import gather
        reserve = gather.rebels_reserve(ctx)  # cap nhat facts.rebels_reserve cho agent (het luot phan quan -> tra quan doan)
    except Exception as e:
        log.debug("rebels_reserve: %s", e)
    if world and getattr(ctx, "mem", None) and hasattr(ctx.mem, "log_march"):
        # P3: % lan quan sat 'Hanh quan' day (report_ro); khong doc duoc cung ghi (used/total None) de dem ti le doc hut
        ctx.mem.log_march(ctx.dev.idx, now, used_total[0] if used_total else None,
                          used_total[1] if used_total else None, reserve, getattr(ctx, "_march_src", None))
    used = used_total[0] if used_total else 0
    rows = ocr.marches(img, used) if used else []
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    travel = (getattr(ctx, "last_dispatch", None) or {}).get("travel") or st.get("last_travel")
    marches = []
    for r in rows:
        rem = r["remaining"]
        m = {"state": r["state"], "remaining": rem}
        if rem is not None:
            if r["state"] == "marching":
                m["arrive_at"] = now + rem
            elif r["state"] == "gathering":
                m["gather_done"] = now + rem
                if travel:
                    m["return_at"] = now + rem + travel
            elif r["state"] == "returning":
                m["return_at"] = now + rem
        marches.append(m)
    _link_dispatches(marches, st.get("dispatches") or [], now)
    for m in marches:
        # thoi gian di ve = thoi gian di toi mo (chu du an 2026-11-21) -> dung dung thoi gian di cua CHINH doi do
        if m["state"] == "gathering" and m.get("gather_done") and m.get("travel"):
            m["return_at"] = m["gather_done"] + m["travel"]
    info = {"resources": res, "resources_at": now, "marches": marches,
            "march_used": used,
            # khung "Hanh quan x/y" chi hien khi co doi dang di -> giu tong so doi da biet
            "march_total": used_total[1] if used_total else st.get("march_total")}
    if travel:
        info["last_travel"] = travel
    if getattr(ctx, "last_dispatch", None):
        info["last_dispatch"] = ctx.last_dispatch
    if getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, **info)
    if getattr(ctx, "mem", None):
        remember(ctx.mem, ctx.dev.idx, info, now)
        ctx.mem.log_observation(getattr(ctx, "visit", None), ctx.dev.idx, info)
    log.info("Tai nguyen %s | hanh quan %s/%s %s", res, used, info["march_total"],
             [(m["state"], m["remaining"]) for m in marches])
    ctx.ensure_city()
    return info


# ---------- khien / thanh tien do (chu du an 2026-11-21) ----------
SHIELD_ICON = (66, 64, 26, 24)       # icon khien duoi VIP: XANH = dang bao ho, xam = "Chua bao ho"
SHIELD_TEXT = (92, 64, 110, 22)


def parse_dur(t):
    """'2d:06:46:45' / '06:46:45' (OCR hay doc 'd' thanh so: '26:06:4645') -> giay | None."""
    t = (t or "").strip()
    m = re.match(r"^\s*(\d{1,2})\s*[dD]\s*:?\s*(\d{1,2})\s*:\s*(\d{2})\s*:?\s*(\d{2})", t)
    if m:
        d, h, mi, s = map(int, m.groups())
        return d * 86400 + h * 3600 + mi * 60 + s
    s = re.sub(r"\D", "", t)
    if len(s) == 6:
        h, mi, se = int(s[:2]), int(s[2:4]), int(s[4:])
        return h * 3600 + mi * 60 + se if mi < 60 and se < 60 else None
    if len(s) in (7, 8, 9):          # ngay (1-2 so) [+ 'd' doc nham thanh 1 so] + hhmmss
        tail = s[-6:]
        head = s[:-6]
        d = int(head[:-1] or head) if len(head) >= 2 and len(s) != 7 else int(head)
        h, mi, se = int(tail[:2]), int(tail[2:4]), int(tail[4:])
        if mi < 60 and se < 60 and h < 24:
            return d * 86400 + h * 3600 + mi * 60 + se
    return None


def read_shield(img):
    """-> {'state': 'on'|'off', 'left': giay|None}. 'Chua bao ho' = off (icon xam)."""
    x, y, w, h = SHIELD_ICON
    hsv = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2HSV)
    blue = int(((hsv[..., 0] >= 85) & (hsv[..., 0] <= 110) & (hsv[..., 1] >= 90) & (hsv[..., 2] >= 150)).sum())
    if blue < 25:
        return {"state": "off", "left": None}
    return {"state": "on", "left": parse_dur(ocr.text(img, SHIELD_TEXT, "0123456789d:", scale=4))}


STRICT = re.compile(r"(?:(\d{1,2})d:)?(\d{2}):(\d{2}):(\d{2})")
FOUR = re.compile(r"(\d{1,3}):(\d{2}):(\d{2}):(\d{2})")


def bar_time(img, bx, by):
    """Doc chu thoi gian tren thanh tien do: OCR nhieu khung lech nhau, chi nhan chuoi DUNG dang (Nd:)hh:mm:ss,
    lay ket qua xuat hien nhieu nhat (OCR chu nho tren nen ray rat nhieu)."""
    votes = {}
    for dx, dy, w, hh in ((7, -4, 95, 15), (5, -3, 95, 14), (2, -4, 105, 16), (0, -4, 112, 15)):
        for b in (None, 140):
            txt = ocr.text(img, (max(0, bx + dx), by + dy, w, hh), "0123456789d:", scale=5, bright=b) or ""
            f4 = FOUR.search(txt)                 # 4 nhom = co ngay; 'd' hay bi doc thanh so ("1d" -> "14")
            if f4 and "d" not in f4.group(1):
                d0 = f4.group(1)
                d = int(d0[:-1]) if len(d0) >= 2 else int(d0)
                h, mi, se = int(f4.group(2)), int(f4.group(3)), int(f4.group(4))
                if h < 24 and mi < 60 and se < 60:
                    v = d * 86400 + h * 3600 + mi * 60 + se
                    votes[v] = votes.get(v, 0) + 1
                continue
            m = STRICT.search(txt)
            if m:
                d, h, mi, se = (int(v) if v else 0 for v in m.groups())
                if h < 24 and mi < 60 and se < 60:
                    v = d * 86400 + h * 3600 + mi * 60 + se
                    votes[v] = votes.get(v, 0) + 1
    return max(votes, key=votes.get) if votes else None


def progress_bars(img, roi=(0, 150, 540, 650)):
    """Thanh tien do tren cong trinh (xay / nghien cuu dang chay): doan XANH sang (H~105, S 255) cao 6-10 px,
    ben phai la ray toi co chu thoi gian trang. -> [(x, y, giay_con_lai | None)]"""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 95) & (hsv[..., 0] <= 115) & (hsv[..., 1] >= 200) & (hsv[..., 2] >= 150)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 5 <= h <= 11 and 3 <= w <= 110 and a >= 0.6 * w * h:
            bx, by = x + x0, y + y0
            t = bar_time(img, bx, by)
            if t is not None or w >= 20:
                out.append((int(bx), int(by), t))
    return out


def base_state(ctx, img, builders=None):
    """Khien + hang cho dang chay (thanh tien do tren cong trinh) -> state.json (web) + timer (lich).
    Chu du an 2026-11-21: "web chua luu trang thai khien, thoi gian con lai; chua luu thoi gian xay / nghien cuu".
    Hiep uoc hoa binh (khien 8h mien phi) can 1 h chuan bi: luc do icon con xam -> state 'off'."""
    now = time.time()
    sh = read_shield(img)
    info = {"shield": {"state": sh["state"], "until": now + sh["left"] if sh.get("left") else None, "at": now}}
    bars = sorted(t for _, _, t in progress_bars(img) if t)
    info["queues"] = [{"until": now + t} for t in bars]
    if builders:
        info["builders"] = {"busy": builders[0], "max": ctx.cfg.get("build", {}).get("max_builders", 1)}
    m = getattr(ctx, "mem", None)
    if m:
        m.clear_timers(ctx.dev.idx, "build:")
        for i, t in enumerate(bars):
            m.set_timer(ctx.dev.idx, f"build:{i}", now + t, "ocr_bar", 0.7)   # lich: ghe khi hang cho xong
        if sh.get("left"):
            m.set_fact(ctx.dev.idx, "shield_until", now + sh["left"])
    if getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, **info)
    log.info("Khien: %s%s | hang cho dang chay: %s", "CO" if sh["state"] == "on" else "chua bao ho",
             f" con {sh['left'] // 3600}h{sh['left'] % 3600 // 60:02d}" if sh.get("left") else "",
             [f"{t // 3600}h{t % 3600 // 60:02d}" for t in bars] or "khong thay")
    return info
