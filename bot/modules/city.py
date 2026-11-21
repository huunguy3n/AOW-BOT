"""Thu tai nguyen noi tren cong trinh trong thanh pho (bieu tuong city/res_*.png)."""
import time, logging

log = logging.getLogger("aow")


def run(ctx):
    ctx.ensure_city()
    names = ctx.v.list("city/res_")
    total = 0
    for _ in range(4):
        img = ctx.shot()
        pts = [p for n in names for p in ctx.v.find_all(img, n)]
        if not pts:
            break
        for x, y, _ in pts:
            ctx.dev.tap(x, y)
            time.sleep(0.4)
            total += 1
        time.sleep(1)
        ctx.close_popups(2)
    ctx.cfg["_use_help"] = ctx.cfg["_use_free"] = True
    ctx.help_and_free()
    log.info("Thu %d bieu tuong tai nguyen trong thanh pho", total)
    return total
