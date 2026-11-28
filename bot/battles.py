"""M2-1 + M2-2 (lo trinh ML, chu du an 2026-11-28 "tich hop M2"): ghi MOI tran / quyet dinh danh-bo vao bang battle_ev
(memory.db) va xac suat thang M2-2 (che do bong) kem theo.

Gan TU BEN NGOAI: install() boc cac ham tran san co (campaign.battle, play.fight, play.power_check,
play._loot_result, play.run, notify.legion_march) thay vi sua tung module - cac module do dang duoc sua o nhanh khac,
va hanh vi danh / bo KHONG doi: wrapper chi goi ham goc roi ghi lai. Moi loi ghi bi nuot (khong lam hong tran).

Loai tran (kind): campaign / intel / expand / mainquest / tutorial (theo buoc dang chay, qua campaign.battle),
arena (dau truong), loot (cuop xe, co ca luc chien ho ve va ta), legion (man quan doan kieu moi: Tinh bao / phan quan,
ket qua chua biet luc xuat chinh).
"""
import functools
import logging
import threading
import time

from aowbot.domain import battle_model

log = logging.getLogger("aow")
_tl = threading.local()
_installed = False
_model = {"at": 0.0, "models": {}, "mem": None}
MODEL_TTL_S = 3600


def _on(ctx):
    return bool(((getattr(ctx, "cfg", None) or {}).get("ml") or {}).get("battle_log", True))


def _ours(ctx):
    """Luc chien tai khoan (observe) - tuong doi, dung khi tran khong doc duoc luc chien doi hinh ta."""
    try:
        from bot.modules import play
        return play._account_power(ctx)
    except Exception:
        return None


def models(mem, now=None):
    """M2-2: mo hinh theo loai tran, fit lai moi gio tu battle_ev (che do bong)."""
    now = time.time() if now is None else now
    if mem is not _model["mem"] or now - _model["at"] > MODEL_TTL_S:
        try:
            rows = mem.query("SELECT kind, ours, enemy, result FROM battle_ev WHERE result IN ('win','lose') "
                             "AND ours IS NOT NULL AND enemy IS NOT NULL ORDER BY at DESC LIMIT 5000")
            _model["models"] = battle_model.fit({"kind": k, "ours": o, "enemy": e, "result": r} for k, o, e, r in rows)
        except Exception as e:
            log.debug("battles.models: %s", e)
            _model["models"] = {}
        _model["at"], _model["mem"] = now, mem
    return _model["models"]


def record(ctx, kind, decision, pred=None, ours=None, enemy=None, result=None, note=None):
    """Ghi 1 dong battle_ev. Loi -> bo qua (log debug)."""
    try:
        mem = getattr(ctx, "mem", None)
        if mem is None or not _on(ctx):
            return
        ours = ours if ours is not None else _ours(ctx)
        m = models(mem).get(kind)
        p = m.p_win(ours, enemy) if m else None
        mem.log_battle(ctx.dev.idx, kind, step=getattr(ctx, "step", None), decision=decision, pred=pred,
                       ours=ours, enemy=enemy, p_win=p, result=result, note=note)
        if p is not None:
            log.info("M2 (bong): %s %s - xac suat thang %.0f %% (ta %s / dich %s) -> %s", kind, decision, 100 * p,
                     ours, enemy, result or "?")
    except Exception as e:
        log.debug("battles.record: %s", e)


def _kind_of(ctx, default):
    st = getattr(ctx, "step", None) or default
    return {"notify": "intel", "reddots": "intel"}.get(st, st)


# ---------------------------------------------------------------- boc ham tran (hanh vi khong doi)
def _wrap_campaign_battle(orig):
    @functools.wraps(orig)
    def battle(ctx, only_win=True, pre_checked=False):
        r = orig(ctx, only_win=only_win, pre_checked=pre_checked)
        fought = r in ("win", "lose")
        record(ctx, _kind_of(ctx, "campaign"), "fight" if fought else str(r),
               pred=("win" if only_win else None) if fought else ("lose" if r == "skip" else None),
               result=r if fought else None)
        return r
    return battle


def _wrap_play_fight(orig):
    @functools.wraps(orig)
    def fight(ctx):
        r = orig(ctx)
        record(ctx, "arena", "fight", result=r if r in ("win", "lose") else None)
        return r
    return fight


def _wrap_power_check(orig):
    @functools.wraps(orig)
    def power_check(guard, ours, margin=0.0):
        res = orig(guard, ours, margin)
        _tl.loot = (guard, ours)
        ctx = getattr(_tl, "ctx", None)
        if ctx is not None and not res[0]:
            record(ctx, "loot", "skip", ours=ours, enemy=guard, note=res[1])
        return res
    return power_check


def _wrap_loot_result(orig):
    @functools.wraps(orig)
    def _loot_result(ctx, *a, **kw):
        r = orig(ctx, *a, **kw)
        guard, ours = getattr(_tl, "loot", (None, None))
        _tl.loot = (None, None)
        record(ctx, "loot", "fight", ours=ours, enemy=guard, result=r if r in ("win", "lose") else None)
        return r
    return _loot_result


def _wrap_play_run(orig):
    @functools.wraps(orig)
    def run(ctx, *a, **kw):
        _tl.ctx = ctx
        try:
            return orig(ctx, *a, **kw)
        finally:
            _tl.ctx = None
    return run


def _wrap_legion_march(orig):
    @functools.wraps(orig)
    def legion_march(ctx):
        r = orig(ctx)
        if r == "lose_pred":
            record(ctx, "legion", "skip", pred="lose")
        elif r != "no_march":
            record(ctx, "legion", "march" if r in (True, "marched", "ok", 1) else str(r), pred="win")
        return r
    return legion_march


WRAPS = (("bot.modules.campaign", "battle", _wrap_campaign_battle),
         ("bot.modules.play", "fight", _wrap_play_fight),
         ("bot.modules.play", "power_check", _wrap_power_check),
         ("bot.modules.play", "_loot_result", _wrap_loot_result),
         ("bot.modules.play", "run", _wrap_play_run),
         ("bot.modules.notify", "legion_march", _wrap_legion_march))


def install():
    """Boc cac ham tran (1 lan / tien trinh). Ham khong ton tai (module doi ten) -> bo qua, log canh bao."""
    global _installed
    if _installed:
        return
    import importlib
    for mod, name, wrap in WRAPS:
        try:
            m = importlib.import_module(mod)
            fn = getattr(m, name)
            if getattr(fn, "_m2_wrapped", False):
                continue
            w = wrap(fn)
            w._m2_wrapped = True
            setattr(m, name, w)
        except Exception as e:
            log.warning("M2: khong gan ghi tran vao %s.%s: %s", mod, name, e)
    _installed = True
