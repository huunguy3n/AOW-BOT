"""Trang thai tung instance + tuy chon tu giao dien web (luu JSON, an toan da luong).

data/state.json    : nhung gi bot quan sat duoc (tai nguyen, hanh quan, trang thai, loi...)
data/settings.json : tuy chon nguoi dung chinh tren web, de len config.yaml
                     {"global": {...}, "instances": {"0": {...}}}
"""
import copy, json, os, threading, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
_lock = threading.RLock()


def _load(name, default):
    p = os.path.join(DATA, name)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_state(state, touched, runner_touched):
    """Ghi state.json KHONG de mat du lieu tien trinh khac (vd 2 runner chay song song, moi cai 1 may):
    doc file hien tai, chi thay cac instance tien trinh nay da sua (+ 'runner' neu da sua)."""
    disk = _load("state.json", {"instances": {}, "runner": {}})
    for k in touched:
        if k in state.get("instances", {}):
            disk.setdefault("instances", {})[k] = state["instances"][k]
        else:
            disk.get("instances", {}).pop(k, None)
    if runner_touched:
        disk["runner"] = state.get("runner", {})
    _save("state.json", disk)
    # lay lai cac may khac tu dia de lan sau khong ghi de ban cu
    for k, v in disk.get("instances", {}).items():
        if k not in touched:
            state.setdefault("instances", {})[k] = v


def _save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    p = os.path.join(DATA, name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class Store:
    def __init__(self):
        self.state = _load("state.json", {"instances": {}, "runner": {}})
        self.settings = _load("settings.json", {"global": {}, "instances": {}})
        self._touched, self._runner_touched = set(), False

    # ---------- trang thai ----------
    def inst(self, idx):
        with _lock:
            return self.state["instances"].setdefault(str(idx), {"enabled": True, "status": "idle"})

    def update(self, idx, **kw):
        with _lock:
            self.inst(idx).update(kw)
            self.inst(idx)["updated"] = time.time()
            self._touched.add(str(idx))
            _save_state(self.state, self._touched, self._runner_touched)

    def runner(self, **kw):
        with _lock:
            self.state.setdefault("runner", {}).update(kw)
            self._runner_touched = True
            _save_state(self.state, self._touched, self._runner_touched)

    # ---------- thong ke theo buoc ----------
    HIST = 20  # so ket qua gan nhat giu lai moi buoc
    MARK = {"ok": "O", "miss": "M", "warn": "W", "err": "E", "stuck": "S"}

    def step_result(self, idx, name, result, dur, shot=None, note=None):
        """Ghi ket qua 1 lan chay buoc: ok | miss (bo qua vi thieu anh mau) | warn (co luu anh debug) | err (exception) | stuck (watchdog).
        stats[name] = {runs, ok, warn, err, stuck, hist:'OOWE..', last_*}"""
        with _lock:
            s = self.inst(idx).setdefault("stats", {}).setdefault(
                name, {"runs": 0, "ok": 0, "warn": 0, "err": 0, "stuck": 0, "hist": ""})
            s["runs"] += 1
            s[result] = s.get(result, 0) + 1
            s["hist"] = (s.get("hist", "") + self.MARK.get(result, "?"))[-self.HIST:]
            s.update(last=result, last_at=time.time(), last_dur=round(dur, 1))
            if result != "ok":
                s.update(bad_at=time.time(), bad_shot=shot, bad_note=note)
            self._touched.add(str(idx))
            _save_state(self.state, self._touched, self._runner_touched)

    def reset_stats(self):
        with _lock:
            for k, st in self.state.get("instances", {}).items():
                st.pop("stats", None)
                self._touched.add(k)
            _save_state(self.state, self._touched, self._runner_touched)

    def snapshot(self):
        with _lock:
            return copy.deepcopy(self.state)

    # ---------- tuy chon ----------
    def cfg_for(self, base_cfg, idx=None):
        """config.yaml + tuy chon chung + tuy chon rieng instance."""
        with _lock:
            c = deep_merge(base_cfg, self.settings.get("global"))
            if idx is not None:
                c = deep_merge(c, self.settings.get("instances", {}).get(str(idx)))
            return c

    def set_settings(self, scope, data):
        with _lock:
            if scope == "global":
                self.settings["global"] = deep_merge(self.settings.get("global", {}), data)
            else:
                ins = self.settings.setdefault("instances", {})
                ins[str(scope)] = deep_merge(ins.get(str(scope), {}), data)
            _save("settings.json", self.settings)

    def get_settings(self):
        with _lock:
            return copy.deepcopy(self.settings)
