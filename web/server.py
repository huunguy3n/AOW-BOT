"""Giao dien quan ly: python main.py --web  ->  http://localhost:8080

Chi nghe tren 127.0.0.1 (may nay). Muon xem tu dien thoai cung mang LAN: --host 0.0.0.0 (khong co mat khau!).
"""
import logging, os, time
from flask import Flask, jsonify, redirect, request, send_from_directory

from aowbot.domain import rollout
from aowbot.domain import warday as warday_rules
from web.options import MODULES, GROUPS
from bot.vnames import fix_name

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(os.path.dirname(HERE), "logs", "shots")


def get_path(d, key):
    for k in key.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def set_path(key, value):
    out = cur = {}
    parts = key.split(".")
    for k in parts[:-1]:
        cur = cur.setdefault(k, {})
    cur[parts[-1]] = value
    return out


def rebels_info(mem, idx, cfg):
    """Tien do Phan quan tap kich hom nay cho web: luot da danh / muc tieu, nha chinh du cap chua."""
    if not mem:
        return None
    try:
        from bot import scheduler
        rc = cfg.get("rebels", {})
        done = scheduler.rebels_done_today(mem, idx, reset_utc=scheduler.sched_cfg(cfg)["daily_reset_utc"])
        hq = mem.fact(idx, "hq_level")
        return {"done": done, "target": rc.get("daily_target", 5), "min_hq": rc.get("min_hq_level", 15),
                "hq": hq, "locked": hq is not None and hq < rc.get("min_hq_level", 15)}
    except Exception:  # web khong duoc chet vi so lieu phu
        return None


def timers_info(mem, idx):
    """Hen gio trong tri nho (xay / nghien cuu / khien) de web hien tien do du state.json chua co."""
    if not mem:
        return None
    try:
        t = [{"key": k, "due": d, "conf": c} for k, d, c, _ in mem.timers(idx) if k.startswith(("build", "research"))]
        return {"list": t, "shield_until": mem.fact(idx, "shield_until")}
    except Exception:
        return None


def week_info(mem, idx, c, now=None):
    """Lich tuan su kien (chu du an 2026-11-23): 'war' (cua so chien tranh - giu khien) | 'gather' (thu 2) | None."""
    from bot import scheduler
    now = now or time.time()
    try:
        if mem is not None and scheduler.war_window(mem, idx, c, now) is not None:
            return "war"
    except Exception:   # noqa: BLE001 - web khong duoc chet vi tri nho hong
        return None
    return "gather" if warday_rules.is_gather_day(warday_rules.wcfg(c.get("warday")), now) else None


def create_app(runner, store, ring):
    app = Flask(__name__)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    base = runner.base_cfg

    @app.get("/")
    def index():
        return send_from_directory(HERE, "index.html")

    @app.get("/api/state")
    def state():
        snap = store.snapshot()
        g = store.cfg_for(base)
        inst = []
        for idx in base["instances"]:
            s = snap["instances"].get(str(idx), {})
            c = store.cfg_for(base, idx)
            mem = getattr(runner, "mem", None)
            bo = [{"step": b[0], "fails": b[1], "until": b[2], "note": b[3]} for b in mem.backoffs(idx)] if mem else []
            rs = s.get("research")
            if isinstance(rs, dict) and rs.get("name"):   # ten cu luu truoc khi co fix_name: sua luc hien thi
                s = {**s, "research": {**rs, "name": fix_name(rs["name"])}}
            inst.append({**s, "idx": idx, "enabled": s.get("enabled", True), "backoff": bo, "rebels": rebels_info(mem, idx, c), "timers": timers_info(mem, idx),
                         "smart": g.get("schedule", {}).get("mode") == "smart",
                         "mode": (c.get("schedule") or {}).get("mode"),
                         "agent": rollout.agent_status(c),     # P6: on | blocked (cong tac chung tat) | off
                         "week": week_info(mem, idx, c),       # lich tuan su kien: war | gather | None
                         "modules": {k: bool(c["modules"].get(k)) for k, _ in MODULES}})
        opts = [{"group": name, "items": [{**o, "value": get_path(g, o["key"])} for o in items]}
                for name, items in GROUPS]
        return jsonify(now=time.time(), runner={**snap.get("runner", {}), "alive": runner.running,
                       "queue": list(runner.queue)}, instances=inst, modules=MODULES, options=opts,
                       agent_switch=rollout.agent_switch(g))

    @app.post("/api/runner")
    def runner_ctl():
        act = (request.json or {}).get("action")
        if act == "start":
            runner.start()
        elif act == "stop":
            runner.stop()
        return jsonify(ok=True)

    @app.post("/api/instance/<int:idx>/unbackoff")
    def unbackoff(idx):
        step = (request.json or {}).get("step")
        if step and getattr(runner, "mem", None):
            runner.mem.step_ok(idx, step)
        return jsonify(ok=True)

    @app.post("/api/instance/<int:idx>/enable")
    def enable(idx):
        store.update(idx, enabled=bool((request.json or {}).get("enabled")))
        return jsonify(ok=True)

    @app.post("/api/instance/<int:idx>/run")
    def run_now(idx):
        runner.run_now(idx)
        return jsonify(ok=True)

    @app.post("/api/instance/<int:idx>/shield")
    def shield_now(idx):
        runner.defend_now(idx)
        return jsonify(ok=True)

    @app.post("/api/instance/<int:idx>/module")
    def module(idx):
        j = request.json or {}
        store.set_settings(idx, {"modules": {j["name"]: bool(j["on"])}})
        return jsonify(ok=True)

    @app.post("/api/instance/<int:idx>/mode")
    def set_mode(idx):
        """Che do theo may: lich chung (xoa ghi de) | agent | demo (hoc mau: bot dung yen ghi thao tac cua ban)."""
        m = (request.json or {}).get("mode")
        if m not in ("", "agent", "demo", "follow"):
            return jsonify(ok=False, error="che do khong hop le"), 400
        if m:
            store.set_settings(idx, {"schedule": {"mode": m}})
        else:
            store.unset_setting(idx, "schedule.mode")
        return jsonify(ok=True)

    @app.post("/api/option")
    def option():
        j = request.json or {}
        known = {o["key"]: o for _, items in GROUPS for o in items}
        if j.get("key") not in known:
            return jsonify(ok=False, error="unknown option"), 400
        store.set_settings("global", set_path(j["key"], j["value"]))
        return jsonify(ok=True)

    @app.post("/api/stats/reset")
    def stats_reset():
        store.reset_stats()
        return jsonify(ok=True)

    @app.get("/shots/<name>")
    def shot(name):
        # chi file anh trong logs/shots (khong cho di ra ngoai thu muc)
        if os.path.basename(name) != name or not name.endswith(".png"):
            return "", 404
        return send_from_directory(SHOTS, name)

    # ---------- giai doan I: "Bot hoc duoc gi" + chu du an day bot ----------
    ROOT = os.path.dirname(HERE)
    IMG_DIRS = {"unknown": os.path.join(ROOT, "logs", "unknown"), "human": os.path.join(ROOT, "logs", "human"),
                "cand": os.path.join(ROOT, "data", "learn", "cand"), "tpl": os.path.join(ROOT, "templates")}

    def _safe(kind, rel):
        base = IMG_DIRS.get(kind)
        if not base or not rel or ".." in rel.replace("\\", "/").split("/"):
            return None
        p = os.path.normpath(os.path.join(base, rel))
        return p if p.startswith(os.path.normpath(base)) and p.endswith(".png") and os.path.exists(p) else None

    # /hoc va /agent da gop vao tab "Học & Agent" cua trang chinh; giu URL cu de link/bookmark khong gay
    @app.get("/hoc")
    @app.get("/agent")
    def learn_agent_page():
        return redirect("/#hoc")

    @app.get("/api/agent")
    def agent_api():
        """B-UI: quyet dinh gan nhat cua agent (bang decisions) + su kien dang hen (bang events). Chi doc."""
        import json as _json
        lim = min(int(request.args.get("limit", 30)), 200)
        q = runner.mem.query
        has = {r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('decisions','events')")}
        decisions = [dict(zip(("at", "account", "action", "next_eval_at", "why", "dry_run", "outcome", "detail"), r))
                     for r in (q("SELECT at, account, action, next_eval_at, why, dry_run, outcome, detail FROM decisions "
                                 "ORDER BY id DESC LIMIT ?", (lim,)) if "decisions" in has else [])]
        for d in decisions:
            d["options"] = (_json.loads(d.pop("detail") or "{}")).get("options", [])
        events = [dict(zip(("account", "type", "due_at", "status", "note"), r))
                  for r in (q("SELECT account, type, due_at, status, note FROM events WHERE status IN ('pending','claimed') "
                              "ORDER BY due_at LIMIT 50") if "events" in has else [])]
        cfgs = {str(i): store.cfg_for(runner.base_cfg, i) for i in runner.base_cfg["instances"]}
        modes = {i: (c.get("schedule") or {}).get("mode") for i, c in cfgs.items()}
        status = {i: rollout.agent_status(c) for i, c in cfgs.items()}
        return jsonify(now=time.time(), decisions=decisions, events=events, modes=modes, status=status,
                       switch=rollout.agent_switch(store.cfg_for(runner.base_cfg)))

    @app.post("/api/agent/switch")
    def agent_switch():
        """P6: cong tac chung agent.enabled (chi nhan true/false that). Tat = dung khan cap agent tren moi may."""
        on = (request.json or {}).get("on")
        if not isinstance(on, bool):
            return jsonify(ok=False, error="on phai la true/false"), 400
        store.set_settings("global", {"agent": {"enabled": on}})
        return jsonify(ok=True, on=on)

    @app.get("/api/learn")
    def learn_api():
        from bot import learn
        try:
            s = learn.summary(runner.mem)
        except Exception as e:
            return jsonify(ok=False, error=str(e)), 500
        unk = sorted(os.listdir(IMG_DIRS["unknown"]), reverse=True) if os.path.isdir(IMG_DIRS["unknown"]) else []
        s["unknown"] = [f for f in unk if f.endswith(".png")][:40]
        hum = []
        hd = IMG_DIRS["human"]
        for day in sorted(os.listdir(hd), reverse=True)[:2] if os.path.isdir(hd) else []:
            for f in sorted(os.listdir(os.path.join(hd, day)), reverse=True):
                if f.endswith("_mark.png"):
                    hum.append(f"{day}/{f}")
        s["human"] = hum[:40]
        s["labels"] = list(learn.SCREEN_LABELS)
        from bot import screen_types
        s["types"], s["intents"] = screen_types.catalog(), screen_types.INTENTS
        try:
            from bot import human_review
            s["human_queue"] = human_review.pending(runner.vision)
        except Exception as e:      # hang cho loi khong duoc lam hong ca trang
            s["human_queue"], s["human_queue_error"] = [], str(e)
        return jsonify(s)

    @app.get("/learnimg/<kind>/<path:rel>")
    def learn_img(kind, rel):
        p = _safe(kind, rel)
        if not p:
            return "", 404
        return send_from_directory(os.path.dirname(p), os.path.basename(p))

    @app.post("/api/learn/teach")
    def learn_teach():
        """Chu du an day 1 man: loai man (goc hoac chi tiet) + cho cham + muc dich (thoat / nhan / tien trinh / mo).
        src='human': tu hang cho thao tac tay (khong xoa anh goc); mac dinh: man la (xoa khoi logs/unknown)."""
        import cv2
        from bot import human_review, screen_types
        j = request.json or {}
        human = j.get("src") == "human"
        p = human_review.path_of(j.get("file")) if human else _safe("unknown", j.get("file", ""))
        kind = j.get("type") or j.get("label")          # 'label' = ten cu (chi loai goc)
        if not p or not kind:
            return jsonify(ok=False, error="file/loai man khong hop le"), 400
        if kind != "skip":
            x, y = j.get("x"), j.get("y")
            err = screen_types.teach(runner.mem, runner.vision, cv2.imread(p), j["file"], kind, j.get("intent"),
                                     None if x is None else int(x), None if y is None else int(y),
                                     "human" if human else "unknown")
            if err:
                return jsonify(ok=False, error=err), 400
        if human:
            human_review.mark_done(j["file"], "skip" if kind == "skip" else f"taught:{kind}")
        else:
            os.remove(p)
        return jsonify(ok=True)

    @app.post("/api/learn/type")
    def learn_type():
        """Them loai man chi tiet (ten tieng Viet + loai goc + co 'bot khong lam theo')."""
        from bot import screen_types
        j = request.json or {}
        try:
            key = screen_types.add(j.get("vn"), j.get("parent"), j.get("no_follow"), j.get("note") or "")
        except ValueError as e:
            return jsonify(ok=False, error=str(e)), 400
        return jsonify(ok=True, key=key)

    @app.post("/api/learn/candidate")
    def learn_candidate():
        """Duyet bien the anh mau ung vien: approve -> hoi quy + chep vao templates/; reject -> danh dau bo."""
        from bot import learn
        j = request.json or {}
        status, res = learn.review_candidate(j.get("tpl"), j.get("hash"), j.get("action") == "approve")
        if status != "ok":
            return jsonify(ok=False), 400 if status == "bad" else 404
        if res:
            runner.vision.reload_variants()
        return jsonify(ok=True, promoted=bool(res))

    @app.post("/api/learn/variant/remove")
    def learn_variant_remove():
        """Go bien the anh mau da hoc (duyet nham) -> data/learn/removed/, bot thoi dung ngay."""
        from bot import learn
        if not learn.remove_variant((request.json or {}).get("path")):
            return jsonify(ok=False), 400
        runner.vision.reload_variants()
        return jsonify(ok=True)

    @app.get("/api/logs")
    def logs():
        n = int(request.args.get("n", 200))
        return jsonify(lines=list(ring.lines)[-n:])

    from web import perception_api
    perception_api.register(app)
    return app


def serve(runner, store, ring, port=8080, host="127.0.0.1"):
    app = create_app(runner, store, ring)
    print(f"Giao dien quan ly: http://localhost:{port}")
    app.run(host=host, port=port, threaded=True, use_reloader=False)
