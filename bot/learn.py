"""Giai doan E + F (docs/bot/05-ke-hoach-hoc-may-mini.md): bot hoc tu chinh nhung lan cham cua minh.

E  Nhat ky kinh nghiem: moi lan cham -> (buoc, ai cham, anh mau, diem, toa do) + KET QUA do o lan chup ke tiep
   (man doi / vung quanh diem cham doi / cham do bien mat / hien bang thuong) -> bang `exp` (memory.db),
   anh cat quanh diem cham -> data/exp/crops/ (bo trung theo dHash, co tran).
   Thong ke ti le thanh cong theo (anh mau, o luoi 24px): cho nao cham hoai khong an -> 'cho chet'.
F1 Bo phan loai man hinh kNN (numpy thuan, cosine): moi man da nhan ra (identify) -> vector dac trung luu vao
   `screen_samples`. Gap man 'unknown' -> hang xom gan nhat cho biet man giong loai nao + nut dong/quay lai o dau.
F2 Anh mau tu mo rong: man la ma nut dong/quay lai khop 0,65-0,82 -> cham thu; man doi -> luu bien the ung vien
   (data/learn/cand/). Dung >= 2 lan, khong lan nao sai, qua hoi quy tests/fixtures/screens -> chep thanh
   templates/<ten>@auto<N>.png (vision.py tu dung bien the).

AN TOAN: chi hoc tren nut DONG / QUAY LAI / HUY (LEARNABLE). Khong bao gio hoc hay tu bam nut nhan thuong, mua,
nang cap... (ADR-0008). Moi loi trong module nay bi nuot (khong lam hong luot chay).
"""
import glob, json, logging, os, shutil, threading, time
import cv2, numpy as np

log = logging.getLogger("aow")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROPS = os.path.join(BASE, "data", "exp", "crops")
CAND = os.path.join(BASE, "data", "learn", "cand")
TPL = os.path.join(BASE, "templates")
CROPS_MAX = 20000            # ~ 20000 x 10 KB = 200 MB
GRID = 24                    # o luoi thong ke vi tri cham

# chi cac nut nay duoc hoc bien the / duoc cham theo hang xom kNN (dong, quay lai, huy thoat game)
LEARNABLE = ["common/btn_x", "common/btn_close", "common/btn_x_small", "common/btn_x_red", "common/tap_to_continue",
             "common/tap_to_close", "common/btn_confirm_hero", "campaign/btn_done", "campaign/btn_done_lose",
             "common/btn_back", "common/btn_back2", "common/btn_cancel_exit"]


# ---------------------------------------------------------------- dac trung anh
def thumb(img):
    return cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (54, 96), interpolation=cv2.INTER_AREA).astype(np.int16)


def feat(img):
    """Vector dac trung man hinh (1632 chieu, chuan hoa L2): anh xam 27x48 (bo trung binh) + histogram mau HSV
    theo luoi 4x3 + mat do bien 9x16. Do 2026-11-20 tren 127 anh co nhan (bo-1-ra): 1-NN dung 94,5 %,
    hang xom sim >= 0,9 dung 100 % (ban cu chi xam + histogram toan man: 96,7 %) -> du tin de CHAM theo hang xom."""
    sm = cv2.resize(img, (27, 48), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(np.float32).ravel()
    g = (g - g.mean()) / (g.std() + 1e-3) / np.sqrt(len(g))
    hsv = cv2.cvtColor(cv2.resize(img, (54, 96), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV)
    hs = []
    for r in range(4):
        for c in range(3):
            h = cv2.calcHist([hsv[r * 24:(r + 1) * 24, c * 18:(c + 1) * 18]], [0, 1], None, [8, 2], [0, 180, 0, 256]).ravel()
            hs.append(h / (h.sum() + 1e-6))
    e = cv2.Canny(cv2.cvtColor(cv2.resize(img, (108, 192), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY), 80, 160)
    eg = cv2.resize(e.astype(np.float32), (9, 16), interpolation=cv2.INTER_AREA).ravel()
    eg = eg / (np.linalg.norm(eg) + 1e-6)
    v = np.concatenate([g, np.concatenate(hs) / np.sqrt(12), eg * 0.7]).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-6)


FEAT_DIM = 27 * 48 + 12 * 16 + 9 * 16


def dhash(img, n=8):
    g = cv2.cvtColor(cv2.resize(img, (n + 1, n), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    return "%016x" % int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).ravel()), 2)


def box(img, x, y, r):
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(0, int(x) - r), max(0, int(y) - r), min(W, int(x) + r), min(H, int(y) + r)
    return img[y0:y1, x0:x1]


def outcome(before, after, x, y, v=None):
    """Ket qua 1 lan cham (ham thuan, test offline duoc). -> dict changed/diff/local/outcome."""
    from bot.badges import red_dots
    tb, ta = thumb(before), thumb(after)
    diff = float(np.abs(tb - ta).mean())
    local = None
    if x is not None:
        a, b = box(before, x, y, 60), box(after, x, y, 60)
        if a.shape == b.shape and a.size:
            local = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())
    out = "none"
    if v is not None and v.find(after, "common/msg_reward", th=0.75, roi=(60, 170, 420, 130)):
        out = "reward"
    elif x is not None and red_dots(box(before, x, y, 70)) and not red_dots(box(after, x, y, 70)):
        out = "dot_gone"
    elif diff >= 2.0:
        out = "changed"
    elif local is not None and local >= 6.0:
        out = "local"
    return {"changed": int(out != "none"), "diff": round(diff, 2),
            "local": None if local is None else round(local, 1), "outcome": out}


# ---------------------------------------------------------------- bo hoc (1 / tien trinh)
class Learner:
    def __init__(self, mem, cfg=None):
        self.mem = mem
        self.cfg = (cfg or {}).get("learn", {}) or {}
        self.lock = threading.Lock()
        self.stats = {}          # (tpl, gx, gy) -> [ok, n]
        self.backs = {}          # H2: man -> [ok, n] cua phim Back
        self.react = {}          # H1: 'module.ham|anh mau' -> [thoi gian phan ung (s)], timeout tinh = wait
        self.X = None            # kNN: ma tran mau (n x d)
        self.lab, self.det = [], []
        self._load()

    # ----- nap tu memory.db -----
    def _load(self):
        try:
            since = time.time() - self.cfg.get("stats_days", 14) * 86400
            for tpl, x, y, ch in self.mem.query(
                    "SELECT COALESCE(tpl, why), x, y, changed FROM exp WHERE at>? AND x IS NOT NULL AND changed IS NOT NULL",
                    (since,)):
                self._count(tpl, x, y, ch)
            for scr, ch in self.mem.query("SELECT scr, changed FROM exp WHERE at>? AND kind='back' AND scr IS NOT NULL "
                                          "AND changed IS NOT NULL", (since,)):
                b = self.backs.setdefault(scr, [0, 0])
                b[0] += int(bool(ch))
                b[1] += 1
            for why, tpl, r in self.mem.query("SELECT why, tpl, react FROM exp WHERE at>? AND react IS NOT NULL "
                                              "ORDER BY at DESC LIMIT 5000", (since,)):
                self.react.setdefault(f"{why}|{tpl}", []).append(r)
            rows = self.mem.query("SELECT label, detail, x, y, feat FROM screen_samples ORDER BY id DESC LIMIT ?",
                                  (self.cfg.get("knn_max", 6000),))
            rows = [r for r in rows if len(r[4]) == FEAT_DIM * 2]     # bo mau cua phien ban dac trung cu
            if rows:
                self.X = np.stack([np.frombuffer(f, np.float16).astype(np.float32) for *_, f in rows])
                self.lab = [r[0] for r in rows]
                self.det = [(r[1], r[2], r[3]) for r in rows]
        except Exception as e:
            log.warning("Hoc: khong nap duoc du lieu cu: %s", e)

    def _key(self, tpl, x, y):
        return (tpl or "?", int(x) // GRID, int(y) // GRID)

    def _count(self, tpl, x, y, ok):
        s = self.stats.setdefault(self._key(tpl, x, y), [0, 0])
        s[0] += int(bool(ok))
        s[1] += 1

    # ----- E: ghi kinh nghiem -----
    def record(self, rows):
        with self.lock:
            for r in rows:
                if r.get("x") is not None and r.get("changed") is not None:
                    self._count(r.get("tpl") or r.get("why"), r["x"], r["y"], r["changed"])
                if r.get("kind") == "back" and r.get("scr") and r.get("changed") is not None:
                    b = self.backs.setdefault(r["scr"], [0, 0])
                    b[0] += int(bool(r["changed"]))
                    b[1] += 1
        self.mem.log_exp(rows)

    def spot(self, tpl, x, y):
        """-> (ok, n) cua vi tri cham nay."""
        return tuple(self.stats.get(self._key(tpl, x, y), (0, 0)))

    def dead_spot(self, tpl, x, y):
        """Cham o day hoai ma khong an (>= dead_min lan, ti le < dead_rate) -> nen thu cach khac."""
        ok, n = self.spot(tpl, x, y)
        return n >= self.cfg.get("dead_min", 8) and ok / n < self.cfg.get("dead_rate", 0.1)

    # ----- H1: thoi gian cho tu thich nghi -----
    def add_react(self, key, t):
        with self.lock:
            lst = self.react.setdefault(key, [])
            lst.insert(0, round(t, 2))
            del lst[60:]

    def react_wait(self, key, wait_s, min_n=8):
        """Thoi gian cho da hoc cho thao tac 'key': p80 thoi gian game phan ung + 0,35 s on dinh, khong vuot wait_s.
        Lan nao man khong doi trong wait_s duoc tinh = wait_s -> thao tac hay 'khong an' thi khong rut ngan.
        Chua du min_n mau -> None (do them)."""
        lst = self.react.get(key) or []
        if len(lst) < min_n:
            return None
        p80 = float(np.percentile(lst[:40], 80))
        return max(0.3, min(wait_s, p80 + 0.35))

    # ----- H2: chon hanh dong bang Thompson sampling -----
    @staticmethod
    def thompson(arms, rng=np.random):
        """arms: {ten: (ok, n)} -> ten co mau Beta(ok+1, n-ok+1) cao nhat."""
        return max(arms, key=lambda a: rng.beta(arms[a][0] + 1, arms[a][1] - arms[a][0] + 1))

    def choose_close(self, scr, tpl, x, y):
        """Man popup/panel: cham nut dong/quay lai (tpl) hay phim Back? -> 'tap' | 'back'.
        Nut chua co du lieu (< 3 lan) -> 'tap' (mac dinh nhu cu)."""
        ok, n = self.spot(tpl, x, y)
        if n < 3:
            return "tap"
        b = tuple(self.backs.get(scr, (0, 0)))
        return self.thompson({"tap": (ok, n), "back": b})

    @staticmethod
    def save_crop(img, x, y):
        """Anh 96x96 quanh diem cham (bo trung theo dHash) -> ten file hoac None."""
        try:
            c = box(img, x, y, 48)
            if c.size == 0:
                return None
            h = dhash(c)
            os.makedirs(CROPS, exist_ok=True)
            p = os.path.join(CROPS, h + ".png")
            if not os.path.exists(p):
                if len(os.listdir(CROPS)) >= CROPS_MAX:
                    return h
                cv2.imwrite(p, c)
            return h
        except Exception:
            return None

    # ----- F1: kNN man hinh -----
    def add_sample(self, inst, label, detail, x, y, img=None, f=None):
        """Them man da nhan ra; bo qua neu da co mau rat giong cung nhan (giu kNN gon)."""
        try:
            f = feat(img) if f is None else f
            with self.lock:
                if self.X is not None and len(self.lab):
                    sims = self.X @ f
                    i = int(sims.argmax())
                    if sims[i] > self.cfg.get("dup_sim", 0.985) and self.lab[i] == label and self.det[i][0] == detail:
                        return False
                    self.X = np.vstack([self.X, f[None]])
                else:
                    self.X = f[None].copy()
                self.lab.append(label)
                self.det.append((detail, x, y))
            self.mem.log_screen(inst, label, detail, x, y, f.astype(np.float16).tobytes())
            return True
        except Exception as e:
            log.debug("Hoc: add_sample loi %s", e)
            return False

    def predict(self, img=None, f=None, k=5):
        """-> (nhan, do_tin_cay, sim_gan_nhat, (anh mau, x, y) cua hang xom gan nhat cung nhan) hoac None."""
        if self.X is None or not len(self.lab):
            return None
        f = feat(img) if f is None else f
        with self.lock:
            sims = self.X @ f
            idx = np.argsort(-sims)[:k]
            votes = {}
            for i in idx:
                votes[self.lab[i]] = votes.get(self.lab[i], 0.0) + max(float(sims[i]), 0.0)
            lab = max(votes, key=votes.get)
            conf = votes[lab] / (sum(votes.values()) + 1e-6)
            best = next(i for i in idx if self.lab[i] == lab)
            return lab, conf, float(sims[best]), self.det[best]

    # ----- F2: bien the anh mau -----
    def _cand_dir(self, tpl):
        return os.path.join(CAND, tpl.replace("/", "__"))

    def candidate(self, tpl, crop, ok):
        """Ket qua 1 lan cham thu nut 'gan khop'. Du dieu kien -> thang cap thanh bien the that."""
        if tpl not in LEARNABLE or crop is None or crop.size == 0:
            return None
        try:
            d = self._cand_dir(tpl)
            os.makedirs(d, exist_ok=True)
            h = dhash(crop)
            meta_p = os.path.join(d, "meta.json")
            with _META_LOCK:     # A-DUP-2: web duyet ung vien cung luc -> khong mat ghi
                meta = _load_meta(meta_p)
                m = meta.setdefault(h, {"ok": 0, "fail": 0, "first": time.time()})
                m["ok" if ok else "fail"] += 1
                p = os.path.join(d, h + ".png")
                if not os.path.exists(p):
                    cv2.imwrite(p, crop)
                res = None
                if (m["ok"] >= self.cfg.get("promote_ok", 2) and m["fail"] == 0 and not m.get("promoted")
                        and not m.get("rejected")):
                    res = promote(tpl, p)
                    m["promoted" if res else "rejected"] = time.time()
                _save_meta(meta_p, meta)
            return res
        except Exception as e:
            log.warning("Hoc: luu ung vien %s loi: %s", tpl, e)
            return None


_META_LOCK = threading.Lock()   # meta.json ung vien: luong bot (candidate) va web (review_candidate)


def _load_meta(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_meta(path, meta):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    os.replace(tmp, path)


def review_candidate(tpl, h, approve):
    """Chu du an duyet ung vien tren web (truoc day web tu doc/ghi meta.json -> trung lap + dua ghi voi bot).
    -> ('ok', da_nhan) | ('bad', None) | ('missing', None)"""
    if tpl not in LEARNABLE:
        return "bad", None
    meta_p = os.path.join(CAND, tpl.replace("/", "__"), "meta.json")
    with _META_LOCK:
        meta = _load_meta(meta_p)
        m = meta.get(h)
        if not m:
            return "missing", None
        res = None
        if approve:
            res = promote(tpl, os.path.join(os.path.dirname(meta_p), h + ".png"))
            m["promoted" if res else "rejected"] = time.time()
        else:
            m["rejected"] = time.time()
        _save_meta(meta_p, meta)
    return "ok", res


def regress_ok(extra=None):
    """F4: identify tren tests/fixtures/screens phai giu dung nhan khi co them bien the. -> (ok, loi[])"""
    from bot.vision import Vision
    from bot.screens import identify
    v = Vision(TPL, 0.82)
    if extra:
        v.extra = extra          # {ten: [anh]} bien the dang xet, chua ghi vao templates/
    bad = []
    for f in sorted(glob.glob(os.path.join(BASE, "tests", "fixtures", "screens", "*", "*.png"))):
        want = os.path.basename(os.path.dirname(f))
        got, _ = identify(cv2.imread(f), v)
        if got != want:
            bad.append(f"{os.path.relpath(f, BASE)}: {want} -> {got}")
    return not bad, bad


def promote(tpl, cand_path, max_variants=6):
    """Ung vien -> templates/<tpl>@auto<N>.png neu qua hoi quy. -> duong dan moi hoac None."""
    img = cv2.imread(cand_path)
    if img is None:
        return None
    exist = glob.glob(os.path.join(TPL, tpl + "@*.png"))
    if len(exist) >= max_variants:
        log.info("Hoc: %s da du %d bien the - bo qua ung vien", tpl, len(exist))
        return None
    ok, bad = regress_ok({tpl: [img]})
    if not ok:
        log.warning("Hoc: bien the %s lam sai hoi quy (%s) - KHONG nhan", tpl, "; ".join(bad[:3]))
        return None
    n = 1
    while os.path.exists(os.path.join(TPL, f"{tpl}@auto{n}.png")):
        n += 1
    dst = os.path.join(TPL, f"{tpl}@auto{n}.png")
    shutil.copyfile(cand_path, dst)
    log.info("Hoc: them bien the anh mau %s (tu %s)", os.path.relpath(dst, BASE), os.path.basename(cand_path))
    return dst


_inst, _ilock = None, threading.Lock()


def get(mem, cfg=None):
    """Bo hoc dung chung cho moi luong (stats + kNN chung: may nay hoc, may kia huong)."""
    global _inst
    if mem is None:
        return None
    with _ilock:
        if _inst is None or _inst.mem is not mem:
            _inst = Learner(mem, cfg)
        return _inst


# ---------------------------------------------------------------- giai doan I: so lieu cho web "Bot hoc duoc gi"
SCREEN_LABELS = ("city", "world", "popup", "panel", "panel_key", "exit_dialog", "reward", "dialog", "loading", "battle")


def summary(mem, days=3):
    """So lieu cho trang web: ti le cham an theo ngay, truot nhieu nhat, cho chet, kNN, bien the, thoi gian cho da hoc."""
    now = time.time()
    out = {"days": []}
    for d in range(days - 1, -1, -1):
        t1 = now - d * 86400
        r = mem.query("SELECT COUNT(*), SUM(changed IS NOT NULL), SUM(changed=1), SUM(kind='human') FROM exp "
                      "WHERE at>? AND at<=?", (t1 - 86400, t1))
        n, known, ok, human = (r[0] if r else (0, 0, 0, 0))
        out["days"].append({"day": time.strftime("%d/%m", time.localtime(t1)), "taps": n or 0, "known": known or 0,
                            "ok": ok or 0, "human": human or 0})
    since = now - 86400
    out["worst"] = [{"who": w, "n": n, "ok": ok} for w, n, ok in mem.query(
        "SELECT COALESCE(tpl, why), COUNT(*), SUM(changed) FROM exp WHERE at>? AND changed IS NOT NULL AND kind!='human' "
        "GROUP BY 1 HAVING COUNT(*)>=5 ORDER BY COUNT(*)-SUM(changed) DESC LIMIT 10", (since,))]
    L = Learner(mem, {})
    out["dead"] = [{"who": k[0], "x": k[1] * GRID, "y": k[2] * GRID, "ok": v[0], "n": v[1]}
                   for k, v in L.stats.items() if v[1] >= 8 and v[0] / v[1] < 0.1][:20]
    out["knn"] = dict(mem.query("SELECT label, COUNT(*) FROM screen_samples GROUP BY label"))
    out["waits"] = sorted(({"key": k, "n": len(v), "p80": round(float(np.percentile(v[:40], 80)), 2)}
                           for k, v in L.react.items() if len(v) >= 8), key=lambda x: -x["n"])[:15]
    out["variants"] = [os.path.relpath(f, TPL).replace("\\", "/")
                       for f in glob.glob(os.path.join(TPL, "**", "*@*.png"), recursive=True)]
    cands = []
    for d in glob.glob(os.path.join(CAND, "*")):
        p = os.path.join(d, "meta.json")
        meta = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        for h, m in meta.items():
            if not m.get("promoted") and not m.get("rejected"):
                cands.append({"tpl": os.path.basename(d).replace("__", "/"), "hash": h, "ok": m["ok"], "fail": m["fail"]})
    out["candidates"] = cands
    return out


def teach(mem, img, label, x=None, y=None):
    """Chu du an dan nhan man la tren web (giai doan I): nhan man + (tuy chon) cho can cham.
    -> them mau kNN (detail 'human' neu co cho cham: _learned_action se cham dung cho do khi gap man giong)."""
    L = get(mem)
    if L is None:
        L = Learner(mem, {})
    return L.add_sample(-2, label, "human" if x is not None else None, x, y, img)
