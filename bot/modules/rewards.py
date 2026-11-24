"""Nhan qua: thu, diem danh, ruong VIP, qua mien phi... theo kieu "tuyen" (route).

Moi tuyen la 1 thu muc anh mau templates/rewards/<tuyen>/:
  open_1.png, open_2.png ...  cham lan luot de mo bang (vd icon thu -> nut "Nhan tat ca").
                              Khong co open_* -> nhan ngay tren man hinh thanh pho.
  tab_1.png, tab_2.png ...    (tuy chon) cac tab trong bang, vao tung tab roi nhan.
  claim_1.png, claim_2.png .. nut nhan/qua, bam lien tuc den khi het (claim_1 uu tien nhat).
  once_1.png ...              nut LUON hien du da nhan (vd "Doc & nhan nhanh") - chi bam 1 lan moi tab.

Them tuyen moi = tao thu muc anh mau + them ten vao config `rewards.routes`, khong can sua code.
"""
import logging
from bot.badges import red_dots, city_bubbles

log = logging.getLogger("aow")


ONCE_ROI = {"mail": (270, 860, 270, 100)}   # P10-5: "Doc & nhan nhanh" o goc PHAI duoi; "Xoa tat ca da doc" ben trai
ITEM_DOTS = {"mail": (480, 100, 60, 760)}   # cham do tren tung dong thu (s153252: x 515) -> con thu chua doc / chua nhan


def claim_tab(ctx, claims, onces, max_taps, route=None):
    n = ctx.claim_loop(claims, max_taps) if claims else 0
    roi = ONCE_ROI.get(route)
    for o in onces:  # nut luon hien (vd "Doc & nhan nhanh") -> bam 1 lan; P10-5: lap lai (toi 3) khi dong thu con cham do
        for k in range(3):
            if not (ctx.tap_tpl(o, wait=1.5, roi=roi) if roi else ctx.tap_tpl(o, wait=1.5)):
                break
            ctx.dismiss_reward()
            n += 1
            dots_roi = ITEM_DOTS.get(route)
            if not dots_roi or not red_dots(ctx.shot(), dots_roi):
                break
            log.info("Thu: con dong cham do sau 'Doc & nhan nhanh' lan %d - bam lai", k + 1)
    return n


def vip_dots(ctx, max_taps=5):
    """Man 'Dac quyen VIP' (chu du an 2026-11-22: anh 3 cham do - dau '+', ruong goc phai, nut dong ho duoi): bam tung
    cham do tren trang VIP, CHI nhan nut 'Nhan' xanh (claim_buttons theo mau+chu) / dung vat pham VIP da co (nut 'Dung').
    Khong bam nut co gia (khung 'VIP1 gioi han mua' co gia kim cuong, khong co cham do). Anh moi bang luu logs/shots."""
    from bot import tapguard
    g = tapguard.of(ctx)
    n, seen = 0, set()
    for _ in range(max_taps):
        img = ctx.shot()
        dots = [d for d in red_dots(img, (0, 60, 540, 900)) if (d[0] // 30, d[1] // 30) not in seen]
        dots = g.keep("vip", dots)          # P12-2: cham do VIP 2 lan nhan 0 (live4 @414,175) -> bo trong lan ghe
        if not dots:
            break
        x, y = sorted(dots, key=lambda d: (d[1] // 30, d[0]))[0]
        seen.add((x // 30, y // 30))
        tx, ty = (x - 80, y + 18) if y > 850 else (x - 25, y + 22)     # cham do o goc tren-phai; nut dong ho: tam nut o trai-duoi
        ctx.tap(tx, ty, wait=2.0)
        ctx.save_debug("vip_dot")
        got = ctx.claim_buttons()
        after = ctx.shot()
        if (ctx.cfg.get("rewards") or {}).get("use_vip_items", True) and ctx.v.find(after, "rewards/vip/title_activate", th=0.9):
            if ctx.tap_tpl("rewards/vip/btn_use", wait=1.5, th=0.9):
                log.info("VIP: kich hoat bang vat pham (Dung)")
                ctx.dismiss_reward()
                got += 1
        n += got
        log.info("VIP: cham do @%d,%d -> nhan %d", x, y, got)
        g.record("vip", x, y, got > 0, "nhan 0")
        ctx.dismiss_reward()
        ctx.tap_first(["common/btn_close"], wait=1.0)      # dong bang con mo (neu co) de ve trang VIP
    return n


def city_gifts(ctx, max_taps=10):
    """Bong bong HOP QUA noi tren cong trinh (nhan dien theo mau/hinh, khong dung anh mau - bong bong trong suot)."""
    ctx.ensure_city()
    n = 0
    for _ in range(max_taps):
        b = city_bubbles(ctx.shot())
        if not b:
            break
        x, y = b[0]
        ctx.tap(x, y, wait=1.5)
        ctx.dismiss_reward()
        n += 1
        if not ctx.is_home():          # cham mo bang khac (khong phai qua) -> quay ra, dung
            log.info("Bong bong qua @%d,%d mo man khac - dung", x, y)
            ctx.ensure_city()
            break
    return n


def dot_strips(ctx, strips, claims, onces, max_taps, depth=0):
    """Hang tab strips[depth]: cham lan luot tab co cham do; hang cuoi -> nhan. Khong tab nao co cham -> nhan
    o tab dang mo. Cham do o goc tren-phai tab -> cham (x-40, y+14)."""
    if depth == len(strips):
        return claim_tab(ctx, claims, onces, max_taps)
    total, done = 0, set()
    for _ in range(6):
        dots = [d for d in red_dots(ctx.shot(), strips[depth]) if d[0] // 50 not in done]
        if not dots:
            break
        x, y = dots[0]
        done.add(x // 50)
        ctx.tap(x - 40, y + 14, wait=1.2)
        total += dot_strips(ctx, strips, claims, onces, max_taps, depth + 1)
    if not done:
        total += dot_strips(ctx, strips, claims, onces, max_taps, depth + 1)
    return total


def run_route(ctx, prefix, max_taps=30):
    """Chay 1 tuyen; prefix vd 'rewards/mail/'. Tra ve so lan nhan."""
    if prefix == "rewards/city/":
        return city_gifts(ctx, max_taps)
    claims = ctx.v.list(prefix + "claim_")
    onces = ctx.v.list(prefix + "once_")
    if not claims and not onces:
        log.info("Tuyen %s chua co anh mau claim_*/once_*.png - bo qua", prefix)
        return 0
    ctx.ensure_city()
    has_open = bool(ctx.v.list(prefix + "open_"))
    route = prefix.strip("/").split("/")[-1]
    rc = ctx.cfg.get("rewards", {})
    if has_open and rc.get("require_dot", True) and route not in (rc.get("always_open") or []):
        # chi mo khi icon co CHAM DO (game bao co qua) -> khong mo bang vo ich moi luot
        img = ctx.shot()
        p = ctx.v.find(img, prefix + "open_1")
        if p and not any(abs(d[0] - p[0]) <= 60 and abs(d[1] - p[1]) <= 45 for d in red_dots(img)):
            log.info("Tuyen %s: icon khong co cham do - bo qua", route)
            return 0
    if has_open and not ctx.open_route(prefix):
        log.info("Khong mo duoc %s (khong thay %sopen_1)", prefix, prefix)
        return 0
    total = 0
    strip = (ctx.cfg.get("rewards", {}).get("dot_tabs") or {}).get(prefix.strip("/").split("/")[-1])
    if strip and isinstance(strip[0], (list, tuple)):
        # nhieu hang tab long nhau (vd Buoi le: hang Ngay -> hang muc con): duyet cham do tung hang
        total += dot_strips(ctx, strips=[tuple(r) for r in strip], claims=claims, onces=onces, max_taps=max_taps)
        ctx.ensure_city()
        return total
    if strip:
        # tab co cham do (so tren tab che mat chu -> anh mau tab khong khop) -> cham tab theo cham do.
        # P7-3 (chu du an 2026-11-24): nhan het o tab DAU TIEN (dang mo) truoc, roi moi sang tab co cham do
        total += claim_tab(ctx, claims, onces, max_taps, route)
        done = set()
        for _ in range(6):
            dots = [d for d in red_dots(ctx.shot(), tuple(strip)) if d[0] // 50 not in done]
            if not dots:
                break
            x, y = dots[0]
            done.add(x // 50)
            ctx.tap(x - 40, y + 14, wait=1.2)   # cham do o goc tren-phai tab (P10-5: ca tab Bao cao)
            total += claim_tab(ctx, claims, onces, max_taps, route)
        ctx.ensure_city()
        return total
    tabs = ctx.v.list(prefix + "tab_")
    if tabs:
        # P7-3 (chu du an 2026-11-24): tab DAU TIEN (dang mo khi vao bang, khong co anh mau tab_1) cung phai nhan het -
        # truoc day chi nhan o tab_2, tab_3... -> thu o tab dau bi bo, so do thu (1) con mai
        total += claim_tab(ctx, claims, onces, max_taps)
        for t in tabs:
            if ctx.tap_tpl(t, wait=1.2):
                total += claim_tab(ctx, claims, onces, max_taps)
    else:
        total += claim_tab(ctx, claims, onces, max_taps)
    if route == "vip":
        total += vip_dots(ctx)
    ctx.ensure_city()
    return total


def icon_badged(ctx, img, tpl, roi=None):
    """Icon `tpl` (thanh pho) con cham do / so do o goc tren-phai -> (x, y) icon | None."""
    p = ctx.v.find(img, tpl, roi=roi) if ctx.v.has(tpl) else None
    if not p:
        return None
    return p if any(-10 <= d[0] - p[0] <= 60 and -60 <= d[1] - p[1] <= 15 for d in red_dots(img)) else None


def repeat_more(rounds, got, still_badged, max_rounds):
    """P7-3: lap mo icon thu / qua toi khi HET so do. Dung khi het so, lan vua roi khong nhan duoc gi (so do khong
    mat vi ly do khac - vd qua lien minh het luot nhan hom nay), hoac du max_rounds."""
    return bool(still_badged) and got > 0 and rounds < max_rounds


def run_until_clear(ctx, route, max_taps, max_rounds=4):
    """Tuyen co icon thanh pho (thu): lap toi khi icon het so do."""
    prefix = f"rewards/{route}/"
    total, r = 0, 0
    while True:
        n = run_route(ctx, prefix, max_taps)
        total += n
        r += 1
        ctx.ensure_city()
        still = icon_badged(ctx, ctx.shot(), prefix + "open_1")
        if not repeat_more(r, n, still, max_rounds):
            if still and n == 0 and r > 1:
                log.info("Qua [%s]: con so do nhung khong nhan them duoc gi - dung", route)
            return total


GIFT_ICON_ROI = (330, 600, 210, 300)     # icon hop qua lien minh (so do) goc phai duoi thanh pho


def ally_gift_until_clear(ctx, max_rounds=4):
    """P7-3 (anh chu du an 2026-11-24: icon qua so 6): mo "Qua tang lien minh" lap toi khi het so do."""
    from bot.modules import alliance
    total, r = 0, 0
    while r < max_rounds:
        ctx.ensure_city()
        p = icon_badged(ctx, ctx.shot(), "ally/icon_gift", GIFT_ICON_ROI)
        if not p:
            break
        n = alliance.gifts(ctx, p[0] + 16, p[1] - 17)   # gifts() cham (x-16, y+17) = tam icon
        ctx.ensure_city()
        total += n
        r += 1
        if not n:
            log.info("Qua lien minh: so do con nhung khong nhan them duoc (het luot hom nay?) - dung")
            break
    return total


def run(ctx):
    rc = ctx.cfg.get("rewards", {})
    grand = 0
    rounds = rc.get("repeat_rounds", 4)
    for route in rc.get("routes", []):
        try:
            if route == "mail" and rc.get("repeat_until_clear", True):
                n = run_until_clear(ctx, route, rc.get("max_taps_per_route", 30), rounds)
            else:
                n = run_route(ctx, f"rewards/{route}/", rc.get("max_taps_per_route", 30))
        except Exception as e:
            log.warning("Loi tuyen qua %s: %s", route, e)
            ctx.save_debug(f"rewards_{route}")
            ctx.ensure_city()
            continue
        log.info("Qua [%s]: nhan %d lan", route, n)
        grand += n
    if rc.get("ally_gift", True):
        try:
            n = ally_gift_until_clear(ctx, rounds)
            if n:
                log.info("Qua [ally_gift]: nhan %d lan", n)
            grand += n
        except Exception as e:
            log.warning("Loi qua lien minh: %s", e)
            ctx.save_debug("rewards_ally_gift")
            ctx.ensure_city()
    return grand
