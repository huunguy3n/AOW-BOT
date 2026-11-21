"""Nhan dien anh mau bang OpenCV. Thieu anh mau -> canh bao 1 lan, coi nhu khong thay."""
import os, glob, logging, threading
import cv2, numpy as np

log = logging.getLogger("aow")


class Vision:
    def __init__(self, tpl_dir, threshold=0.82):
        self.dir = tpl_dir
        self.th = threshold
        self.cache = {}
        self.missing = set()
        self._tl = threading.local()  # miss_hits rieng tung luong (2 may chay song song, 2026-11-20)
        self.var = {}      # bien the tu hoc: templates/<ten>@*.png (giai doan F2, bot/learn.py)
        self.extra = {}    # bien the dang xet (hoi quy truoc khi nhan) - chi dung trong learn.regress_ok
        self.prior = {}    # G2: (ten, kich thuoc anh) -> vi tri tim thay gan nhat -> tim vung nho quanh do truoc
        self.prior_hits = [0, 0]

    @property
    def miss_hits(self):
        """So lan tra cuu anh mau KHONG co trong luong hien tai (runner dem de danh dau buoc 'thieu anh mau')."""
        return getattr(self._tl, "n", 0)

    @miss_hits.setter
    def miss_hits(self, v):
        self._tl.n = v

    def load(self, name, probe=False):
        """probe=True: chi hoi co anh mau khong (anh mau tuy chon) -> khong canh bao, khong dem miss_hits."""
        if name in self.cache:
            if self.cache[name] is None and not probe:
                self.miss_hits += 1
            return self.cache[name]
        path = os.path.join(self.dir, name + ".png")
        img = cv2.imread(path, cv2.IMREAD_COLOR) if os.path.exists(path) else None
        if probe:
            if img is not None:
                self.cache[name] = img
            return img
        if img is None and name not in self.missing:
            self.missing.add(name)
            log.warning("Thieu anh mau: templates/%s.png", name)
        if img is None:
            self.miss_hits += 1
        self.cache[name] = img
        return img

    def has(self, name):
        return self.load(name, probe=True) is not None

    def variants(self, name):
        """Bien the da duyet cua anh mau (templates/<ten>@*.png) + bien the dang xet."""
        if name not in self.var:
            fs = sorted(glob.glob(os.path.join(self.dir, name + "@*.png")))
            self.var[name] = [im for im in (cv2.imread(f, cv2.IMREAD_COLOR) for f in fs) if im is not None]
        return self.var[name] + self.extra.get(name, [])

    def reload_variants(self):
        self.var = {}

    def _tpls(self, name):
        t = self.load(name)
        return [] if t is None else [t] + self.variants(name)

    def list(self, prefix):
        """Liet ke anh mau theo tien to, vd 'research/tech_' -> sap xep theo ten."""
        files = sorted(glob.glob(os.path.join(self.dir, prefix + "*.png")))
        return [os.path.relpath(f, self.dir)[:-4].replace("\\", "/") for f in files if "@" not in os.path.basename(f)]

    @staticmethod
    def _crop(img, roi):
        if not roi:
            return img, 0, 0
        x, y, w, h = roi
        return img[y:y + h, x:x + w], x, y

    PRIOR_MIN = 0.93   # chi tin vung nho khi khop rat chac (nut lap lai nhieu cho -> van tim ca man)

    def find(self, img, name, th=None, roi=None):
        """Tra ve (cx, cy, score) hoac None. Thu ca bien the tu hoc (lay diem cao nhat).
        G2 (tri nho vi tri): khong co roi -> thu truoc vung +-60 px quanh lan tim thay gan nhat; khop >= 0,93 thi
        dung luon (nhanh hon tim ca man ~5-10 lan), khong thi tim ca man nhu cu."""
        key = (name, img.shape[:2])
        pr = self.prior.get(key) if roi is None else None
        if pr:
            t = self.load(name)
            if t is not None:
                h, w = t.shape[:2]
                x0, y0 = max(0, pr[0] - w // 2 - 60), max(0, pr[1] - h // 2 - 60)
                b = self.best(img, name, roi=(x0, y0, w + 120, h + 120))
                if b and b[2] >= max(th or self.th, self.PRIOR_MIN):
                    self.prior_hits[0] += 1
                    return b
        best = self.best(img, name, roi=roi)
        self.prior_hits[1] += 1
        if best is None or best[2] < (th or self.th):
            return None
        if roi is None and best[2] >= self.PRIOR_MIN:
            self.prior[key] = best[:2]
        return best

    def best(self, img, name, roi=None):
        """Diem khop cao nhat (khong ap nguong) -> (cx, cy, score) hoac None. Dung cho 'gan khop' (F2)."""
        area, ox, oy = self._crop(img, roi)
        out = None
        for t in self._tpls(name):
            if area.shape[0] < t.shape[0] or area.shape[1] < t.shape[1]:
                continue
            res = cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if out is None or mx > out[2]:
                h, w = t.shape[:2]
                out = (ox + loc[0] + w // 2, oy + loc[1] + h // 2, float(mx))
        return out

    def find_all(self, img, name, th=None, roi=None, min_dist=20):
        area, ox, oy = self._crop(img, roi)
        cand = []
        for t in self._tpls(name):
            if area.shape[0] < t.shape[0] or area.shape[1] < t.shape[1]:
                continue
            res = cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(res >= (th or self.th))
            h, w = t.shape[:2]
            cand += [(ox + x + w // 2, oy + y + h // 2, float(res[y, x])) for x, y in zip(xs, ys)]
        out = []
        for cx, cy, sc in sorted(cand, key=lambda p: -p[2]):
            if all(abs(cx - a) > min_dist or abs(cy - b) > min_dist for a, b, _ in out):
                out.append((cx, cy, sc))
        return out
