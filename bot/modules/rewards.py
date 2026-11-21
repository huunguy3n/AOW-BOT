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


def claim_tab(ctx, claims, onces, max_taps):
    n = ctx.claim_loop(claims, max_taps) if claims else 0
    for o in onces:  # nut luon hien (vd "Doc & nhan nhanh") -> chi bam 1 lan
        if ctx.tap_tpl(o, wait=1.5):
            ctx.dismiss_reward()
            n += 1
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
        # tab co cham do (so tren tab che mat chu -> anh mau tab khong khop) -> cham tab theo cham do
        done = set()
        for _ in range(6):
            dots = [d for d in red_dots(ctx.shot(), tuple(strip)) if d[0] // 50 not in done]
            if not dots:
                break
            x, y = dots[0]
            done.add(x // 50)
            ctx.tap(x - 40, y + 14, wait=1.2)   # cham do o goc tren-phai tab
            total += claim_tab(ctx, claims, onces, max_taps)
        if not done:
            total += claim_tab(ctx, claims, onces, max_taps)  # tab dang mo
        ctx.ensure_city()
        return total
    tabs = ctx.v.list(prefix + "tab_")
    if tabs:
        for t in tabs:
            if ctx.tap_tpl(t, wait=1.2):
                total += claim_tab(ctx, claims, onces, max_taps)
    else:
        total += claim_tab(ctx, claims, onces, max_taps)
    ctx.ensure_city()
    return total


def run(ctx):
    rc = ctx.cfg.get("rewards", {})
    grand = 0
    for route in rc.get("routes", []):
        try:
            n = run_route(ctx, f"rewards/{route}/", rc.get("max_taps_per_route", 30))
        except Exception as e:
            log.warning("Loi tuyen qua %s: %s", route, e)
            ctx.save_debug(f"rewards_{route}")
            ctx.ensure_city()
            continue
        log.info("Qua [%s]: nhan %d lan", route, n)
        grand += n
    return grand
