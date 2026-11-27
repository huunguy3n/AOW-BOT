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
import glob, json, logging, os, random, re, shutil, threading, time
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
        self.streak = {}         # (tpl, gx, gy) -> so lan truot LIEN TIEP tu lan an gan nhat (J1: chan cho chet)
        self.probe = {}          # J1: (tpl, gx, gy) -> [lan thu lai ke tiep (epoch), so lan thu lai lien tiep]
        self.skips = 0           # J1: so lan cham bi chan tu luc khoi dong tien trinh
        self.hist = {}           # M1-1/2: 'anh mau|module.ham' -> deque[(gx, gy, dhash vung cham, diem khop, an)]
        self._valid = {}         # M1-1/2: khoa -> (luc kiem, so mau, cho phep?, precision, so du doan) - tu kiem bo-ra
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
                    "SELECT COALESCE(tpl, why), x, y, changed FROM exp WHERE at>? AND x IS NOT NULL AND changed IS NOT NULL "
                    "ORDER BY at", (since,)):
                self._count(tpl, x, y, ch)
            for key, x, y, crop, sc, ch in self.mem.query(
                    "SELECT COALESCE(tpl, why), x, y, crop, score, changed FROM exp WHERE at>? AND x IS NOT NULL "
                    "AND changed IS NOT NULL AND kind NOT IN ('human', 'ml_skip') ORDER BY at", (since,)):
                self._hist_add(key, x, y, crop, sc, ch)
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
        k = self._key(tpl, x, y)
        if ok:
            self.streak.pop(k, None)
            self.probe.pop(k, None)          # cham lai an -> het 'chet', lich thu lai ve 0
        else:
            self.streak[k] = self.streak.get(k, 0) + 1

    # ----- E: ghi kinh nghiem -----
    def record(self, rows):
        with self.lock:
            for r in rows:
                if r.get("x") is not None and r.get("changed") is not None:
                    self._count(r.get("tpl") or r.get("why"), r["x"], r["y"], r["changed"])
                    if r.get("kind") not in ("human", "ml_skip"):
                        self._hist_add(r.get("tpl") or r.get("why"), r["x"], r["y"], r.get("crop"), r.get("score"),
                                       r["changed"])
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

    # ----- J1: chan cham vao cho chet o MOI lan cham cua module -----
    def skip_tap(self, tpl, why, x, y, now=None):
        """Lan cham (anh mau tpl / ham goi why) toi (x, y) co nen BO QUA khong? -> 'skip' | 'probe' | None.
        Chet = dead_spot (ti le an < dead_rate tren >= dead_min lan) VA truot lien tiep >= dead_min lan tu lan an gan
        nhat (1 lan an la song lai). Nut dong/quay lai (LEARNABLE, common/*) va skip_exempt khong bao gio chan.
        Van cho cham THU LAI (probe) moi probe_min phut, gap doi sau moi lan thu truot, toi da probe_cap_h gio
        -> man/nut doi thi bot tu nhan ra (lan thu an -> xoa chet)."""
        c = self.cfg
        if not c.get("skip_dead", True) or x is None or y is None:
            return None
        key = tpl or why
        if not key or tpl in LEARNABLE or (tpl or "").startswith("common/"):
            return None
        if any(key == e or key.startswith(e + "/") or key.startswith(e + ".") for e in c.get("skip_exempt", []) or []):
            return None
        k = self._key(key, x, y)
        with self.lock:
            if self.streak.get(k, 0) < c.get("dead_min", 8) or not self.dead_spot(key, x, y):
                return None
            now = time.time() if now is None else now
            nxt, tries = self.probe.get(k, (0.0, 0))
            if now >= nxt:
                wait = min(c.get("probe_min", 60) * 60 * 2 ** (tries + 1), c.get("probe_cap_h", 24) * 3600)
                self.probe[k] = [now + wait, tries + 1]
                return "probe" if nxt else self._skip_first(k, now)
            self.skips += 1
            return "skip"

    def _skip_first(self, k, now):
        """Lan dau gap cho chet trong tien trinh: chan luon (da biet chet), lan thu lai dau tien sau probe_min."""
        self.probe[k] = [now + self.cfg.get("probe_min", 60) * 60, 0]
        self.skips += 1
        return "skip"

    # ----- M1-1 / M1-2: doan lan cham VO ICH theo anh vung cham + diem khop -----
    # Do offline 27/11/2026 (14 ngay, 77k lan cham, bo-ra 30 % moi nhat): dHash vung 96x96 (Hamming <= 4, cung o luoi
    # +-1, >= 5 hang xom, >= 90 % truot) bo duoc 608/1631 lan truot, dung 98,2 %. Vd ally/tab_main: khop 0,994 ma
    # truot 421 lan = tab DA MO san. Diem khop (+-0,005) la luat du phong khi chua du hang xom theo anh.
    def _hist_add(self, key, x, y, crop, sc, ch):
        if not key or x is None or y is None:
            return
        from collections import deque
        try:
            h = int(crop, 16) if crop else None
        except (TypeError, ValueError):
            h = None
        d = self.hist.get(key)
        if d is None:
            d = self.hist[key] = deque(maxlen=self.cfg.get("noop_keep", 400))
        d.append((int(x) // GRID, int(y) // GRID, h, None if sc is None else float(sc), int(bool(ch))))

    def _noop_vote(self, lst, gx, gy, h, sc):
        """-> 'crop' | 'score' (doan vo ich, kem luat nao), False (doan co tac dung), None (chua du hang xom)."""
        c = self.cfg
        mn, rate = c.get("noop_min_n", 5), c.get("noop_rate", 0.9)
        near = [t for t in lst if abs(t[0] - gx) <= 1 and abs(t[1] - gy) <= 1]
        if h is not None:
            md = c.get("noop_hash_d", 4)
            nb = [t[4] for t in near if t[2] is not None and bin(t[2] ^ h).count("1") <= md]
            if len(nb) >= mn:
                return "crop" if nb.count(0) / len(nb) >= rate else False
        if sc is not None:
            nb = [t[4] for t in near if t[3] is not None and abs(t[3] - sc) <= 0.005]
            if len(nb) >= mn:
                return "score" if nb.count(0) / len(nb) >= rate else False
        return None

    def noop_valid(self, key, now=None):
        """Tu kiem bo-ra cho tung khoa (anh mau / module.ham): hoc 70 % cu, doan 30 % moi -> chi cho chan khi
        precision >= noop_precision va >= noop_min_pred lan doan. Tinh lai moi gio hoac khi them >= 50 mau."""
        now = time.time() if now is None else now
        lst = list(self.hist.get(key) or ())
        v = self._valid.get(key)
        if v and now - v[0] < 3600 and len(lst) - v[1] < 50:
            return v[2]
        ok = False
        tp = fp = 0
        if len(lst) >= self.cfg.get("noop_min_hist", 30):
            cut = int(len(lst) * 0.7)
            train = lst[:cut]
            for gx, gy, h, sc, ch in lst[cut:]:
                if self._noop_vote(train, gx, gy, h, sc):
                    tp += ch == 0
                    fp += ch == 1
            ok = (tp + fp >= self.cfg.get("noop_min_pred", 5)
                  and tp / (tp + fp) >= self.cfg.get("noop_precision", 0.95))
        self._valid[key] = (now, len(lst), ok, round(tp / (tp + fp), 3) if tp + fp else None, tp + fp)
        return ok

    def predict_noop(self, key, x, y, crop_hash=None, score=None, now=None):
        """-> 'crop' | 'score' neu lan cham nay gan nhu chac khong co tac dung, nguoc lai None."""
        if not key or x is None or y is None or not self.noop_valid(key, now):
            return None
        try:
            h = int(crop_hash, 16) if isinstance(crop_hash, str) else crop_hash
        except ValueError:
            h = None
        return self._noop_vote(list(self.hist.get(key) or ()), int(x) // GRID, int(y) // GRID, h,
                               None if score is None else float(score)) or None

    def exempt(self, tpl, why):
        """Khong bao gio chan: nut dong / quay lai (LEARNABLE, common/*), cham 'lam theo mau', skip_exempt."""
        key = tpl or why
        if not key or tpl in LEARNABLE or (tpl or "").startswith("common/") or tpl == "imitate":
            return True
        return any(key == e or key.startswith(e + "/") or key.startswith(e + ".")
                   for e in self.cfg.get("skip_exempt", []) or [])

    def noop_gate(self, tpl, why, x, y, crop_hash=None, score=None, now=None, rng=random.random):
        """MOI lan cham cua module hoi day. -> ('skip', ly do) | ('probe', ly do) | None.
        ly do: 'dead' (J1 cho chet), 'crop' (M1-1 anh vung cham), 'score' (M1-2 diem khop).
        Chan = KHONG gui cham nhung coi nhu da cham (ket qua du doan giong het: khong co gi doi)."""
        if x is None or y is None or self.exempt(tpl, why):
            return None
        r = self.skip_tap(tpl, why, x, y, now)
        if r:
            return (r, "dead")
        if not self.cfg.get("skip_noop", True):
            return None
        why_ = self.predict_noop(tpl or why, x, y, crop_hash, score, now)
        if not why_:
            return None
        if rng() < self.cfg.get("noop_explore", 0.05):     # thinh thoang van cham that de tiep tuc hoc
            return ("probe", why_)
        self.skips += 1
        return ("skip", why_)

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
        if approve and (m.get("fail", 0) > 0 or m.get("ok", 0) < 1):
            return "bad", None      # tung cham sai / chua cham dung lan nao -> khong cho duyet (ke ca goi API tay)
        if approve:
            res = promote(tpl, os.path.join(os.path.dirname(meta_p), h + ".png"))
            m["promoted" if res else "rejected"] = time.time()
        else:
            m["rejected"] = time.time()
        _save_meta(meta_p, meta)
    return "ok", res


def remove_variant(rel):
    """Go 1 bien the da hoc (vd duyet nham): templates/<tpl>@autoN.png -> data/learn/removed/. -> True neu da go."""
    rel = (rel or "").replace("\\", "/")
    base, _, tail = rel.partition("@")
    if base not in LEARNABLE or not re.fullmatch(r"auto\d+\.png", tail):
        return False
    src = os.path.join(TPL, rel)
    if not os.path.isfile(src):
        return False
    dst_dir = os.path.join(BASE, "data", "learn", "removed")
    os.makedirs(dst_dir, exist_ok=True)
    shutil.move(src, os.path.join(dst_dir, f"{int(time.time())}-{rel.replace('/', '__')}"))
    log.info("Hoc: chu du an go bien the anh mau %s", rel)
    return True


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
        r = mem.query("SELECT SUM(kind!='ml_skip'), SUM(changed IS NOT NULL), SUM(changed=1), SUM(kind='human'), "
                      "SUM(kind='ml_skip') FROM exp WHERE at>? AND at<=?", (t1 - 86400, t1))
        n, known, ok, human, skip = (r[0] if r else (0, 0, 0, 0, 0))
        out["days"].append({"day": time.strftime("%d/%m", time.localtime(t1)), "taps": n or 0, "known": known or 0,
                            "ok": ok or 0, "human": human or 0, "ml_skip": skip or 0})
    since = now - 86400
    L = _inst if _inst is not None and _inst.mem is mem else Learner(mem, {})   # bo hoc dang chay (da tu kiem san)
    out["worst"] = [{"who": w, "n": n, "ok": ok} for w, n, ok in mem.query(
        "SELECT COALESCE(tpl, why), COUNT(*), SUM(changed) FROM exp WHERE at>? AND changed IS NOT NULL AND kind!='human' "
        "GROUP BY 1 HAVING COUNT(*)>=5 ORDER BY COUNT(*)-SUM(changed) DESC LIMIT 10", (since,))]
    out["dead"] = [{"who": k[0], "x": k[1] * GRID, "y": k[2] * GRID, "ok": v[0], "n": v[1]}
                   for k, v in L.stats.items() if v[1] >= 8 and v[0] / v[1] < 0.1][:20]
    # J1: cham ML da chan (cho chet) 24h, theo ai cham + buoc
    out["ml_skips"] = [{"who": w, "step": st, "why": r or "dead", "n": n} for w, st, r, n in mem.query(
        "SELECT COALESCE(tpl, why), step, outcome, COUNT(*) FROM exp WHERE at>? AND kind='ml_skip' "
        "GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 15", (since,))]
    out["scoreboard"] = scoreboard(mem)
    out["noop"] = noop_status(L)
    out["knn"] = dict(mem.query("SELECT label, COUNT(*) FROM screen_samples GROUP BY label"))
    # hop thoai "Roi tro choi?" bot tu bat (moi lan = 1 lan bam Huy) theo buoc, 24h -> web theo doi sau sua press_back
    out["exit_dialogs"] = [{"step": st, "n": n} for st, n in mem.query(
        "SELECT step, COUNT(*) FROM exp WHERE at>? AND tpl='common/btn_cancel_exit' AND kind!='human' "
        "GROUP BY step ORDER BY 2 DESC", (now - 86400,))]
    out["waits"] = sorted(({"key": k, "n": len(v), "p80": round(float(np.percentile(v[:40], 80)), 2)}
                           for k, v in L.react.items() if len(v) >= 8), key=lambda x: -x["n"])[:15]
    out["variants"] = [os.path.relpath(f, TPL).replace("\\", "/")
                       for f in glob.glob(os.path.join(TPL, "**", "*@*.png"), recursive=True)]
    cands = []
    for d in glob.glob(os.path.join(CAND, "*")):
        p = os.path.join(d, "meta.json")
        meta = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        for h, m in meta.items():
            # chi dua len web ung vien CO THE dung: da cham dung >= 1 lan va chua lan nao sai
            # (cham sai = vung do khong phai nut -> khong bao gio duyet, vd nen mo sau popup, mat nhan vat)
            if not m.get("promoted") and not m.get("rejected") and m.get("fail", 0) == 0 and m.get("ok", 0) >= 1:
                cands.append({"tpl": os.path.basename(d).replace("__", "/"), "hash": h, "ok": m["ok"], "fail": m["fail"]})
    out["candidates"] = cands
    return out


def scoreboard(mem, days=7, now=None):
    """M0 (lo trinh ML, docs/strategy/ml-roadmap.md): so do chung theo NGAY (gio may) -> list dict, cu -> moi.
    taps/ok_pct: cham co ket qua (bo cham tay + cham ML chan); skip_*: ML chan theo ly do; visits / visit_min /
    machine_h: luot ghe da xong, phut trung binh, may-gio (tran 48 = 2 luong x 24 h); errs: buoc loi + luot ghe loi /
    ngat; hq: {may: cap nha chinh cuoi ngay} tu fact hq_history."""
    now = time.time() if now is None else now
    t_end = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1)) + 86400    # nua dem toi nay
    hist = {}
    try:
        for inst, val in mem.query("SELECT inst, value FROM facts WHERE key='hq_history'"):
            hist[inst] = sorted((float(t), int(lv)) for t, lv in json.loads(val))
    except Exception:
        pass
    out = []
    for d in range(days - 1, -1, -1):
        t1 = t_end - d * 86400
        t0 = t1 - 86400
        r = mem.query("SELECT SUM(changed IS NOT NULL AND kind NOT IN ('human','ml_skip')), "
                      "SUM(changed=1 AND kind NOT IN ('human','ml_skip')), "
                      "SUM(kind='ml_skip' AND COALESCE(outcome,'dead')='dead'), SUM(kind='ml_skip' AND outcome='crop'), "
                      "SUM(kind='ml_skip' AND outcome='score') FROM exp WHERE at>=? AND at<?", (t0, t1))
        known, ok, sd, sc, ss = [v or 0 for v in (r[0] if r else (0,) * 5)]
        v = mem.query("SELECT COUNT(*), SUM(ended-started), SUM(result IN ('error','interrupted')) FROM visits "
                      "WHERE started>=? AND started<? AND ended IS NOT NULL", (t0, t1))
        nv, dur, verr = [x or 0 for x in (v[0] if v else (0, 0, 0))]
        e = mem.query("SELECT SUM(result='err'), SUM(result='warn') FROM runs WHERE started>=? AND started<?", (t0, t1))
        rerr, rwarn = [x or 0 for x in (e[0] if e else (0, 0))]
        hq = {}
        for inst, h in hist.items():
            before = [lv for t, lv in h if t < t1]
            if before:
                hq[inst] = before[-1]
        out.append({"day": time.strftime("%d/%m", time.localtime(t0)), "taps": known, "ok": ok,
                    "ok_pct": round(100 * ok / known, 1) if known else None,
                    "skip_dead": sd, "skip_crop": sc, "skip_score": ss, "skips": sd + sc + ss,
                    "visits": nv, "visit_min": round(dur / nv / 60, 1) if nv else None,
                    "machine_h": round(dur / 3600, 1), "step_err": rerr, "step_warn": rwarn, "visit_err": verr,
                    "hq": hq})
    return out


def noop_status(L, top=15):
    """M1-1/2: khoa nao dang duoc phep chan (tu kiem bo-ra dat) -> list cho web / report."""
    rows = []
    keys = sorted(L.hist, key=lambda k: -sum(1 for t in L.hist[k] if not t[4]))[:40]   # khoa truot nhieu nhat
    for key in keys:
        L.noop_valid(key)
        v = L._valid.get(key)
        if v and v[4]:
            rows.append({"key": key, "n": v[1], "on": v[2], "precision": v[3], "pred": v[4]})
    return sorted(rows, key=lambda r: (-r["on"], -r["pred"]))[:top]


def teach(mem, img, label, x=None, y=None):
    """Chu du an dan nhan man la tren web (giai doan I): nhan man + (tuy chon) cho can cham.
    -> them mau kNN (detail 'human' neu co cho cham: _learned_action se cham dung cho do khi gap man giong)."""
    L = get(mem)
    if L is None:
        L = Learner(mem, {})
    return L.add_sample(-2, label, "human" if x is not None else None, x, y, img)
