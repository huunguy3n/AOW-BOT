"""Tri nho lau dai cua bot: data/memory.db (SQLite, thu vien chuan).

Ke hoach: docs/product/ke-hoach-A-tri-nho-lap-lich.md
  visits       : moi lan bat may 1 tai khoan (bat -> tat), de tinh thoi gian may bat            (A0)
  runs         : moi lan chay 1 buoc (ket qua, thoi gian, gia tri module tra ve)                (A0)
  observations : ket qua observe cuoi luot (hanh quan, tai nguyen)                              (A0)
  timers       : khi nao viec gi xong (doi quan ve, xay xong, nghien cuu xong...) - "goi y"     (A1)
  facts        : du kien tai khoan (cap nha chinh, so doi, tan thu xong...)                     (A1)
  backoff      : buoc loi lien tiep -> tam bo toi 'until'                                       (A4)
Tri nho chi la GOI Y; man hinh la su that -> module thay khac thi ghi de.

Nguyen tac: loi DB KHONG BAO GIO duoc lam hong luot chay -> moi ham ghi deu nuot loi va chi canh bao 1 lan.
Khong ghi thong tin xac thuc vao day.
"""
import json, logging, os, pathlib, sqlite3, threading, time

log = logging.getLogger("aow")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "memory.db")
VERSION = 4

SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
  id INTEGER PRIMARY KEY, inst INTEGER NOT NULL, started REAL NOT NULL, ended REAL,
  result TEXT, why TEXT, mode TEXT);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, visit INTEGER, inst INTEGER NOT NULL, step TEXT NOT NULL,
  started REAL NOT NULL, dur REAL, result TEXT, note TEXT, ret TEXT, why TEXT);
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY, visit INTEGER, inst INTEGER NOT NULL, at REAL NOT NULL,
  march_used INTEGER, march_total INTEGER, marches TEXT, resources TEXT);
CREATE TABLE IF NOT EXISTS timers (
  inst INTEGER NOT NULL, key TEXT NOT NULL, due_at REAL NOT NULL, src TEXT, conf REAL, updated REAL,
  PRIMARY KEY (inst, key));
CREATE TABLE IF NOT EXISTS facts (
  inst INTEGER NOT NULL, key TEXT NOT NULL, value TEXT, seen_at REAL, PRIMARY KEY (inst, key));
CREATE TABLE IF NOT EXISTS backoff (
  inst INTEGER NOT NULL, step TEXT NOT NULL, fails INTEGER NOT NULL, until REAL, last_note TEXT,
  PRIMARY KEY (inst, step));
CREATE TABLE IF NOT EXISTS nav (
  id INTEGER PRIMARY KEY, visit INTEGER, inst INTEGER, step TEXT, at REAL, screen TEXT, action TEXT, changed INTEGER);
CREATE TABLE IF NOT EXISTS exp (
  id INTEGER PRIMARY KEY, visit INTEGER, inst INTEGER, step TEXT, at REAL, kind TEXT, tpl TEXT, why TEXT,
  x INTEGER, y INTEGER, score REAL, scr TEXT, changed INTEGER, diff REAL, local REAL, outcome TEXT, lat REAL, crop TEXT);
CREATE TABLE IF NOT EXISTS screen_samples (
  id INTEGER PRIMARY KEY, inst INTEGER, at REAL, label TEXT, detail TEXT, x INTEGER, y INTEGER, ok INTEGER, feat BLOB);
CREATE TABLE IF NOT EXISTS perf (
  id INTEGER PRIMARY KEY, visit INTEGER, inst INTEGER, step TEXT, at REAL, kind TEXT, src TEXT,
  n INTEGER, total REAL, p50 REAL, p90 REAL, max REAL);
CREATE TABLE IF NOT EXISTS queue_obs (
  inst INTEGER NOT NULL, at REAL NOT NULL, kind TEXT NOT NULL, used INTEGER, total INTEGER);
CREATE TABLE IF NOT EXISTS march_obs (
  inst INTEGER NOT NULL, at REAL NOT NULL, used INTEGER, total INTEGER, reserve INTEGER, src TEXT);
CREATE TABLE IF NOT EXISTS gather_ev (
  inst INTEGER NOT NULL, at REAL NOT NULL, kind TEXT NOT NULL, rtype TEXT, level INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS gem_ev (
  inst INTEGER NOT NULL, at REAL NOT NULL, src TEXT NOT NULL, n INTEGER NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS battle_ev (
  id INTEGER PRIMARY KEY, inst INTEGER NOT NULL, at REAL NOT NULL, kind TEXT NOT NULL, step TEXT, decision TEXT,
  pred TEXT, ours INTEGER, enemy INTEGER, p_win REAL, result TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS battle_kind_t ON battle_ev(kind, at);
CREATE INDEX IF NOT EXISTS exp_tpl ON exp(tpl, x, y);
CREATE INDEX IF NOT EXISTS runs_inst_t ON runs(inst, started);
CREATE INDEX IF NOT EXISTS visits_inst_t ON visits(inst, started);
CREATE INDEX IF NOT EXISTS obs_inst_t ON observations(inst, at);
"""


def _js(v):
    """Gia tri -> JSON ngan (bo qua thu khong serialize duoc)."""
    if v is None:
        return None
    try:
        s = json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        s = json.dumps(str(v))
    return s[:2000]


class Memory:
    def __init__(self, path=DB, readonly=False):
        """readonly: mo `mode=ro`, KHONG chay schema / PRAGMA user_version (A-REL-2: truoc day cong cu bao cao
        cung ghi vao DB that). Ham ghi o che do nay that bai -> canh bao 1 lan, nhu loi DB khac."""
        self.path = path
        self.readonly = readonly
        self._local = threading.local()
        self._warned = False
        try:
            self._conn()
        except Exception as e:
            self._warn(e)

    def _conn(self):
        c = getattr(self._local, "c", None)
        if c is None and self.readonly:
            uri = pathlib.Path(self.path).resolve().as_uri() + "?mode=ro"
            c = sqlite3.connect(uri, uri=True, timeout=10, isolation_level=None)
            c.execute("PRAGMA busy_timeout=10000")
            self._local.c = c
        if c is None:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            c = sqlite3.connect(self.path, timeout=10, isolation_level=None)  # autocommit
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=10000")
            c.executescript(SCHEMA)
            try:
                c.execute("ALTER TABLE exp ADD COLUMN react REAL")   # H1: thoi gian game phan ung (s); them sau, VERSION van la 4
            except sqlite3.OperationalError:
                pass
            c.execute(f"PRAGMA user_version={VERSION}")
            self._local.c = c
        return c

    def _warn(self, e):
        if not self._warned:
            log.warning("Tri nho (memory.db) loi, bo qua ghi: %s", e)
            self._warned = True

    def _exec(self, sql, args=()):
        try:
            return self._conn().execute(sql, args)
        except Exception as e:
            self._warn(e)
            return None

    # ---------- ghi ----------
    def visit_start(self, inst, why=None, mode="fixed"):
        cur = self._exec("INSERT INTO visits(inst, started, why, mode) VALUES (?,?,?,?)",
                         (inst, time.time(), why, mode))
        return cur.lastrowid if cur else None

    def visit_end(self, visit, result):
        if visit:
            self._exec("UPDATE visits SET ended=?, result=? WHERE id=?", (time.time(), result, visit))

    def close_open_visits(self, result="interrupted"):
        """Lan ghe dang do khi tien trinh chet (web tat theo ung dung, 2026-11-19 13:16 / 21:23) -> dong lai,
        ended = luc buoc cuoi ket thuc (khong co buoc -> luc bat dau). Goi luc runner khoi dong."""
        r = self.query("SELECT id, inst FROM visits WHERE ended IS NULL")
        self.open_insts = sorted({i for _, i in r or []})
        for vid, _ in r or []:
            self._exec("UPDATE visits SET ended=COALESCE((SELECT MAX(started+dur) FROM runs WHERE visit=?), started), "
                       "result=? WHERE id=?", (vid, result, vid))
        return len(r or [])

    def log_run(self, visit, inst, step, started, dur, result, note=None, ret=None, why=None):
        self._exec("INSERT INTO runs(visit, inst, step, started, dur, result, note, ret, why) VALUES (?,?,?,?,?,?,?,?,?)",
                   (visit, inst, step, started, round(dur, 2), result, note, _js(ret), why))

    def log_observation(self, visit, inst, info):
        self._exec("INSERT INTO observations(visit, inst, at, march_used, march_total, marches, resources) VALUES (?,?,?,?,?,?,?)",
                   (visit, inst, info.get("resources_at") or time.time(), info.get("march_used"),
                    info.get("march_total"), _js(info.get("marches")), _js(info.get("resources"))))

    def log_nav(self, visit, inst, step, rows):
        """Nhat ky goto() cua 1 buoc (giai doan C). changed = hanh dong CUA DONG NAY co lam man doi khong
        (truoc 2026-11-20 ghi lech 1 dong: changed cua hanh dong truoc); None = chua biet (hanh dong cuoi)."""
        try:
            c, now = self._conn(), time.time()
            c.executemany("INSERT INTO nav(visit, inst, step, at, screen, action, changed) VALUES (?,?,?,?,?,?,?)",
                          [(visit, inst, step, now, s, a, None if ch is None else int(ch)) for s, a, ch in rows])
        except Exception as e:
            self._warn(e)

    def log_queues(self, inst, at, queues):
        """Q0: anh chup hang cho (tho xay / nghien cuu / huan luyen) - do 'hang cho ranh bao lau' (report_ro)."""
        rows = [(inst, at, k, v[0], v[1]) for k, v in queues.items() if v]
        if not rows:
            return
        try:
            self._conn().executemany("INSERT INTO queue_obs(inst, at, kind, used, total) VALUES (?,?,?,?,?)", rows)
        except Exception as e:
            self._warn(e)

    def log_march(self, inst, at, used, total, reserve=0, src=None):
        """P3: 1 lan quan sat 'Hanh quan x/y' cuoi luot (observe). used/total None = khong doc duoc (van ghi de dem).
        reserve = so quan doan de danh cho phan quan (gather dung som co chu dich) - report_ro tinh 'day' = used >= total - reserve."""
        self._exec("INSERT INTO march_obs(inst, at, used, total, reserve, src) VALUES (?,?,?,?,?,?)",
                   (inst, at, used, total, reserve or 0, src))

    def log_gather(self, inst, kind, rtype=None, level=None, note=None):
        """P3: su kien thu thap (sent, own_skip, own_dialog = Huy oan, contested, dialog_unknown, occupied, not_found,
        unread, cap_table, too_big, full, no_troops) -> report_ro dem theo loai."""
        self._exec("INSERT INTO gather_ev(inst, at, kind, rtype, level, note) VALUES (?,?,?,?,?,?)",
                   (inst, time.time(), kind, rtype, level, None if note is None else str(note)[:200]))

    def log_gem(self, inst, src, n, note=None):
        """P6: so kim cuong bot da tieu (src: shield = khien khi bi tan cong, shield_war = khien ngay chien tranh).
        report_ro tong hop theo nguon; nguon ngoai khien = vi pham ADR-0008. Khong ghi thong tin dang nhap."""
        self._exec("INSERT INTO gem_ev(inst, at, src, n, note) VALUES (?,?,?,?,?)",
                   (inst, time.time(), src, int(n), None if note is None else str(note)[:200]))

    def log_battle(self, inst, kind, step=None, decision=None, pred=None, ours=None, enemy=None, p_win=None,
                   result=None, note=None):
        """M2-1: 1 tran / 1 quyet dinh danh-bo (kind: campaign, intel, expand, arena, loot, legion...).
        decision: fight | skip | ...; pred: du doan cua game (win | lose | None); result: win | lose | None (chua biet).
        p_win: xac suat thang cua M2-2 (che do bong, chi ghi)."""
        self._exec("INSERT INTO battle_ev(inst, at, kind, step, decision, pred, ours, enemy, p_win, result, note) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (inst, time.time(), kind, step, decision, pred, ours, enemy,
                    None if p_win is None else round(float(p_win), 4), result,
                    None if note is None else str(note)[:200]))

    def log_perf(self, visit, inst, step, rows):
        """A-MEAS-1: tong hop bo dem hieu nang cua 1 buoc (bot/perf.py Perf.drain())."""
        if not rows:
            return
        try:
            now = time.time()
            self._conn().executemany(
                "INSERT INTO perf(visit, inst, step, at, kind, src, n, total, p50, p90, max) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(visit, inst, step, now, *r) for r in rows])
        except Exception as e:
            self._warn(e)

    # ---------- kinh nghiem (giai doan E) ----------
    def log_exp(self, rows):
        """rows: dict theo cot bang exp. Ghi theo lo."""
        if not rows:
            return
        cols = ("visit", "inst", "step", "at", "kind", "tpl", "why", "x", "y", "score", "scr", "changed", "diff",
                "local", "outcome", "lat", "crop", "react")
        try:
            self._conn().executemany(f"INSERT INTO exp({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                                     [tuple(r.get(k) for k in cols) for r in rows])
        except Exception as e:
            self._warn(e)

    def log_screen(self, inst, label, detail, x, y, feat, ok=None):
        """Mau man hinh co nhan (tu identify) cho bo phan loai kNN (giai doan F1). feat: float16 bytes."""
        self._exec("INSERT INTO screen_samples(inst, at, label, detail, x, y, ok, feat) VALUES (?,?,?,?,?,?,?,?)",
                   (inst, time.time(), label, detail, x, y, ok, feat))

    # ---------- timers ----------
    def set_timer(self, inst, key, due_at, src="ocr", conf=1.0):
        self._exec("INSERT OR REPLACE INTO timers(inst, key, due_at, src, conf, updated) VALUES (?,?,?,?,?,?)",
                   (inst, key, float(due_at), src, conf, time.time()))

    def clear_timers(self, inst, prefix):
        self._exec("DELETE FROM timers WHERE inst=? AND key LIKE ?", (inst, prefix + "%"))

    def timers(self, inst, prefix=""):
        """-> [(key, due_at, conf, src)] sap theo due_at."""
        return self.query("SELECT key, due_at, conf, src FROM timers WHERE inst=? AND key LIKE ? ORDER BY due_at",
                          (inst, prefix + "%"))

    # ---------- facts ----------
    def set_fact(self, inst, key, value):
        self._exec("INSERT OR REPLACE INTO facts(inst, key, value, seen_at) VALUES (?,?,?,?)",
                   (inst, key, _js(value), time.time()))

    def fact(self, inst, key, default=None):
        r = self.query("SELECT value FROM facts WHERE inst=? AND key=?", (inst, key))
        if not r or r[0][0] is None:
            return default
        try:
            return json.loads(r[0][0])
        except Exception:
            return default

    def facts(self, inst):
        out = {}
        for k, v, t in self.query("SELECT key, value, seen_at FROM facts WHERE inst=?", (inst,)):
            try:
                out[k] = json.loads(v) if v is not None else None
            except Exception:
                out[k] = v
        return out

    # ---------- backoff ----------
    def backoff_until(self, inst, step):
        r = self.query("SELECT until FROM backoff WHERE inst=? AND step=?", (inst, step))
        return r[0][0] if r and r[0][0] else 0

    def step_failed(self, inst, step, note, base_min=30, cap_h=6):
        """Loi/ket lien tiep -> tam bo min(base x 2^(n-1), cap). Tra ve thoi diem het tam bo."""
        r = self.query("SELECT fails FROM backoff WHERE inst=? AND step=?", (inst, step))
        n = (r[0][0] if r else 0) + 1
        until = time.time() + min(base_min * 60 * 2 ** (n - 1), cap_h * 3600)
        self._exec("INSERT OR REPLACE INTO backoff(inst, step, fails, until, last_note) VALUES (?,?,?,?,?)",
                   (inst, step, n, until, (note or "")[:300]))
        return until

    def step_ok(self, inst, step):
        self._exec("DELETE FROM backoff WHERE inst=? AND step=?", (inst, step))

    def backoffs(self, inst):
        return self.query("SELECT step, fails, until, last_note FROM backoff WHERE inst=? AND until>?", (inst, time.time()))

    # ---------- doc (cho tools/baseline.py) ----------
    def query(self, sql, args=()):
        cur = self._exec(sql, args)
        return cur.fetchall() if cur else []
