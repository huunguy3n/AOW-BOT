"""Ngu canh cho moi tai khoan: chup man hinh, tim & cham anh mau, dieu huong chung."""
import os, re, time, random, logging
import cv2, numpy as np

from bot import perf

log = logging.getLogger("aow")


class Stuck(BaseException):
    """Watchdog: man hinh dung yen qua lau / buoc chay qua gio. Ke thua BaseException de cac
    'except Exception' trong module khong nuot mat; runner bat rieng va khoi dong lai game."""


class Ctx:
    def __init__(self, dev, vision, cfg):
        self.dev, self.v, self.cfg = dev, vision, cfg
        self.W = cfg["screen"]["width"]
        self.H = cfg["screen"]["height"]
        self._img = None
        # he so thoi gian cho sau moi lan cham (chu du an 2026-11-20: "thao tac con cham") - config speed.wait_scale
        self.wait_scale = float((cfg.get("speed") or {}).get("wait_scale", 1.0))
        self.debug_shots = []      # anh save_debug trong luot (runner dem de biet buoc co 'canh bao')
        self.nav = []              # nhat ky goto(): (man, hanh dong, man co doi) - runner ghi vao tri nho
        self.step = None
        # giai doan E: kinh nghiem cham (bot/learn.py). _pend = lan cham dang cho ket qua (do o lan chup ke tiep)
        self._pend, self._exp, self._img_t, self._probe = None, [], 0.0, None
        # watchdog: mac dinh TAT (cong cu tools/* dung Ctx truc tiep); runner bat theo config 'watchdog'
        self.wd_enabled = False
        wd = cfg.get("watchdog", {})
        self.wd_still = wd.get("still_min", 5) * 60
        self.wd_diff = wd.get("diff_th", 2.0)
        self.wd_reset()

    # ---------- watchdog ----------
    def wd_reset(self, step_limit=None):
        """Bat dau dem lai (dau moi buoc / sau khi khoi dong lai game). step_limit: giay toi da cho buoc."""
        self._wd_t = self._wd_changed = time.time()
        self._wd_thumb = None
        self.step_limit = step_limit

    def _watch(self, img):
        """So anh thu nho voi anh moc gan nhat: lech trung binh >= diff_th coi nhu man hinh da doi."""
        now = time.time()
        g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (54, 96), interpolation=cv2.INTER_AREA).astype(np.int16)
        if self._wd_thumb is None or float(np.abs(g - self._wd_thumb).mean()) >= self.wd_diff:
            self._wd_thumb, self._wd_changed = g, now
        if now - self._wd_changed > self.wd_still:
            raise Stuck(f"man hinh dung yen {(now - self._wd_changed) / 60:.1f} phut")
        if self.step_limit and now - self._wd_t > self.step_limit:
            raise Stuck(f"buoc chay qua {self.step_limit / 60:.0f} phut")

    # ---------- co ban ----------
    def shot(self):
        from bot import steer
        steer.wait_battle()   # may kia dang lai quan -> nhuong CPU
        self._img = self.dev.screencap()
        self._img_t = time.time()
        if self._pend:
            self._exp_end(self._img)
        if self.wd_enabled:
            self._watch(self._img)
        return self._img

    def find(self, name, fresh=True, **kw):
        img = self.shot() if fresh or self._img is None else self._img
        return self.v.find(img, name, **kw)

    def tap_tpl(self, name, wait=1.2, fresh=True, dy=0, **kw):
        p = self.find(name, fresh=fresh, **kw)
        if not p:
            return False
        log.debug("tap %s @%d,%d (%.2f)", name, p[0], p[1], p[2])
        self._exp_begin("tpl", p[0], p[1] + dy, name, p[2])
        self.dev.tap(p[0], p[1] + dy)
        self._after_tap(wait * self.wait_scale)
        return True

    def tap_first(self, names, wait=1.2, **kw):
        img = self.shot()
        for n in names:
            p = self.v.find(img, n, **kw)
            if p:
                self._exp_begin("first", p[0], p[1], n, p[2])
                self.dev.tap(p[0], p[1])
                self._after_tap(wait * self.wait_scale)
                return n
        return None

    def wait_for(self, name, timeout=6.0, interval=0.6, **kw):
        t0 = time.time()
        while time.time() - t0 < timeout:
            p = self.find(name, **kw)
            if p:
                return p
            time.sleep(interval)
        return None

    def settle(self, max_s=3.0, interval=0.35, th=1.5):
        """S1: chup toi khi 2 khung lien tiep gan nhu giong nhau (camera ngung truot, bang mo xong) hoac het
        max_s -> anh on dinh (cung la self._img). Vi sao: sau 'Den' game truot camera toi cong trinh; kiem tra
        sau mot khoang cho co dinh thay man dang chay -> tra 'none' du nut Tang cap hien ngay sau do."""
        from bot import screens
        t0 = time.time()
        prev = self.shot()
        while time.time() - t0 < max_s:
            time.sleep(interval)
            img = self.shot()
            if screens.same(prev, img, th):
                return img
            prev = img
        return prev

    human_pause = None   # P9-1: bot.hang.HumanPause (runner gan khi bat HumanWatch)

    def human_gate(self, why=""):
        """P9-1: chu du an dang cham tay lien tiep -> cho tay yen roi moi cham (khong giam len thao tac cua chu)."""
        hp = self.human_pause
        if hp is None:
            return 0.0
        waited = hp.wait(why or f"o buoc {self.step}")
        if waited:
            self.wd_reset(self.step_limit)   # thoi gian cho chu khong tinh vao watchdog cua buoc
            self._img = None
        return waited

    def tap(self, x, y, wait=1.0, tpl=None):
        self.human_gate()
        self._exp_begin("tap", x, y, tpl)
        self.dev.tap(x, y)
        self._after_tap(wait * self.wait_scale)

    def _after_tap(self, wait_s):
        """H1: cho sau khi cham. Da hoc thoi gian game phan ung cua thao tac nay -> cho p80 + 0,35 s (khong vuot
        wait_s). Chua du mau (hoac 15 % lan de do lai) -> chup lien tuc toi khi man doi, ghi thoi gian phan ung."""
        p = self._pend
        L = self.learner
        if not p or not L or not (self.cfg.get("learn") or {}).get("adaptive_wait", True) or wait_s < 0.5:
            time.sleep(wait_s)
            return
        key = f"{p.get('why')}|{p.get('tpl')}"
        w = L.react_wait(key, wait_s)
        before = p.get("_before")
        if w is not None and (random.random() > 0.15 or before is None):
            time.sleep(w)
            return
        if before is None:
            time.sleep(wait_s)
            return
        from bot import screens
        t0 = time.time()
        time.sleep(0.15)
        while time.time() - t0 < wait_s:
            try:
                img = self.dev.screencap(tries=1)
            except Exception:
                break
            if not screens.same(before, img):
                r = time.time() - t0
                L.add_react(key, r)
                p["react"] = round(r, 2)
                time.sleep(0.25)                       # cho hoat anh mo bang on dinh
                return
        L.add_react(key, wait_s)
        p["react"] = round(wait_s, 2)
    # ---------- giai doan E: kinh nghiem ----------
    @property
    def learner(self):
        m = getattr(self, "mem", None)
        if m is None or not (self.cfg.get("learn") or {}).get("enabled", True):
            return None
        from bot import learn
        return learn.get(m, self.cfg)

    @staticmethod
    def _caller():
        """Ham goi thao tac (bo qua cac ham cua Ctx) -> 'module.ham' de biet ai cham."""
        import sys
        f = sys._getframe(2)
        while f and f.f_code.co_filename.endswith("ctx.py"):
            f = f.f_back
        if not f:
            return None
        return f"{os.path.splitext(os.path.basename(f.f_code.co_filename))[0]}.{f.f_code.co_name}"

    def _exp_begin(self, kind, x, y, tpl=None, score=None):
        """Ghi nhan 1 lan cham; ket qua do o lan shot() ke tiep. Loi -> bo qua (khong lam hong luot)."""
        try:
            if self.learner is None:
                return
            if self._pend:
                self._exp_end(None)        # 2 lan cham lien khong chup giua -> lan truoc khong biet ket qua
            fresh = self._img is not None and time.time() - self._img_t < 5
            self._pend = {"visit": getattr(self, "visit", None), "inst": self.dev.idx, "step": self.step,
                          "at": time.time(), "kind": kind, "tpl": tpl, "why": self._caller(),
                          "x": None if x is None else int(x), "y": None if y is None else int(y),
                          "score": None if score is None else round(float(score), 3),
                          "scr": getattr(self, "_scr_now", None), "_before": self._img if fresh else None}
            self._scr_now = None
        except Exception as e:
            log.debug("exp_begin: %s", e)
            self._pend = None

    def _exp_end(self, after):
        p, self._pend = self._pend, None
        try:
            before = p.pop("_before")
            p["lat"] = round(time.time() - p["at"], 2)
            if before is not None and after is not None:
                from bot import learn
                p.update(learn.outcome(before, after, p["x"], p["y"], self.v))
                if p["x"] is not None:
                    p["crop"] = learn.Learner.save_crop(before, p["x"], p["y"])
            self._exp.append(p)
            pr, self._probe = self._probe, None
            if pr and p.get("changed") is not None and self.learner:   # F2: cham thu nut 'gan khop'
                from bot import screens
                # dung = man doi VA man moi nhan ra duoc (dieu huong tien len), khong chi 'co gi do chuyen dong'
                good = bool(p["changed"]) and screens.identify(after, self.v)[0] != "unknown"
                if self.learner.candidate(pr[0], pr[1], good):
                    self.v.reload_variants()
            if len(self._exp) >= 40:
                self.exp_flush()
        except Exception as e:
            log.debug("exp_end: %s", e)

    def exp_flush(self):
        """Ghi kinh nghiem dang giu vao memory.db (runner goi cuoi moi buoc)."""
        rows, self._exp = self._exp, []
        if self._pend and time.time() - self._pend["at"] > 30:
            self._exp_end(None)
            rows, self._exp = rows + self._exp, []
        L = self.learner
        if L and rows:
            L.record(rows)
        return len(rows)

    def save_debug(self, tag):
        os.makedirs("logs/shots", exist_ok=True)
        path = f"logs/shots/{time.strftime('%Y%m%d-%H%M%S')}-i{self.dev.idx}-{tag}.png"
        try:
            cv2.imwrite(path, self.dev.screencap())  # khong qua shot(): khong kich watchdog
        except Exception:
            pass
        self.debug_shots.append(path)
        return path

    # ---------- dieu huong chung ----------
    # btn_net_retry: "Mang ngoai le - Mang bi ngat ket noi" luc vao game -> "Thu lai" (do #5 2026-11-18)
    # btn_rebuild: "Do ben Xuong kien truc giam xuong 0 ... Xay dung lai" (bi danh khi offline) - nut duy nhat, mien phi
    # btn_x_red: X do goc phai man CONGRATULATIONS (ket qua chieu mo / nhan tuong) - ket ca luot #0 2026-11-19 07:41
    POPUP_CLOSERS = ["common/btn_confirm_hero", "common/btn_net_retry", "common/btn_rebuild", "common/btn_x", "common/btn_close", "common/btn_x_small", "common/btn_x_red", "common/tap_to_continue", "common/tap_to_close"]

    def cancel_exit(self, img=None, why=""):
        """Hop thoai "Roi tro choi?" dang mo -> bam HUY (khong bao gio Xac nhan). Hien do phim Back o thanh pho/ban do
        (cua bot, nguoi choi hoac game). Goi truoc moi lan bam nut dong/xac nhan chung. -> True neu da Huy."""
        img = img if img is not None else self.shot()
        p = self.v.find(img, "common/btn_cancel_exit")
        if not p:
            return False
        log.warning("Hop thoai thoat game dang mo (%s, buoc %s) -> Huy", why or "?", getattr(self, "step", "?"))
        self.tap(p[0], p[1], wait=0.8, tpl="common/btn_cancel_exit")
        return True

    def close_popups(self, rounds=5, settle=0):
        """settle>0: khi het popup thi doi them settle giay, xem co popup moi hien tiep khong
        (luc vao game cac popup hien noi tiep nhau)."""
        retried = False
        for _ in range(rounds):
            if self.cancel_exit(why="close_popups"):
                continue
            if self.tap_first(self.POPUP_CLOSERS, wait=0.8):
                retried = False
                continue
            if settle and not retried:
                retried = True
                time.sleep(settle)
                continue
            return

    def back_out(self, rounds=4):
        """Thoat cac bang dang mo bang nut quay lai (hoac phim Back).
        Nut "Dong" cua man ket qua tran bam TRUOC nut "<" (chu du an 2026-11-20: "bam Dong truoc, dang bam < truoc")."""
        for _ in range(rounds):
            if self.is_home():
                return
            if not self.tap_first(["campaign/btn_done", "campaign/btn_done_lose", "common/btn_back", "common/btn_back2"]
                                  + self.POPUP_CLOSERS, wait=0.8):
                if not self.press_back("back_out"):
                    return                       # da ve thanh pho / ban do

    def safe_back(self):
        """Phim Back CHI khi khong o thanh pho / ban do the gioi: o do Back chi hien hop thoai "Roi tro choi?"
        (chu du an 2026-11-20: "vi sao instance nay lien tuc muon roi tro choi"). -> True neu da bam."""
        return self.press_back("key_back")

    def press_back(self, why):
        """MOI lan bam phim Back cua bot di qua day (chu du an 2026-11-21: bam thoat game ~130 lan/ngay).
        - Dang o thanh pho / ban do -> KHONG bam (Back o do = hop thoai "Roi tro choi?").
        - Kiem 2 lan cach 0,5 s: ngay sau khi xuat chinh / chuyen ban do, ban do con truot -> is_home doc truot 1 lan.
        - Van hien hop thoai thoat -> Huy + ghi canh bao kem ly do (de biet ai con bam sai).
        -> True neu da bam Back."""
        if self.is_home():
            return False
        time.sleep(0.5)
        if self.is_home():
            return False
        self._exp_begin("back", None, None, why)
        self.dev.back()
        time.sleep(0.8)
        if self.tap_tpl("common/btn_cancel_exit", wait=0.6):
            log.warning("Phim Back (%s, buoc %s) mo hop thoai thoat game -> da Huy", why, getattr(self, "step", "?"))
        return True

    def is_home(self):
        img = self.shot()
        return bool(self.v.find(img, "common/btn_to_world") or self.v.find(img, "common/btn_to_city"))

    def _world_open(self, ok):
        """Nho ban do the gioi da mo chua (scheduler.world_ready) - tranh thu lai moi buoc khi chua mo."""
        m = getattr(self, "mem", None)
        if m and (m.fact(self.dev.idx, "world_open") != ok):
            log.info("Ban do the gioi: %s", "da mo" if ok else "CHUA mo - bo cac buoc can ban do")
        if m:
            m.set_fact(self.dev.idx, "world_open", ok)
        if getattr(self, "store", None):
            self.store.update(self.dev.idx, world_open=ok)

    def world_ready(self):
        from bot import scheduler
        m = getattr(self, "mem", None)
        return scheduler.world_ready(m, self.dev.idx, self.cfg) if m else True

    def goto(self, target="city", rounds=10):
        """Giai doan B: nhan dien man (bot/screens.py) -> hanh dong -> lap lai toi khi o man dich.
        target: city | world | home. Ghi nhat ky dieu huong (giai doan C): (man, hanh dong, hanh dong co lam man doi).
        Cham ma man khong doi 2 lan lien tiep -> doi sang phim Back. Man la -> luu logs/unknown/ de dan nhan.
        Giai doan E/F: man nhan ra -> mau kNN; man la -> hoi kNN / cham thu nut dong 'gan khop';
        nut o 'cho chet' (cham >= 8 lan hau nhu khong an) -> Back luon. Tra ve True neu toi dich."""
        from bot import screens
        L = self.learner
        prev, stale = None, 0
        for _ in range(rounds):
            img = self.shot()
            scr, act, arg = screens.nav_action(img, self.v, target)
            changed = prev is None or not screens.same(prev, img)
            stale = 0 if changed else stale + 1
            if prev is not None and self.nav:
                s0, a0, _ = self.nav[-1]
                self.nav[-1] = (s0, a0, changed)       # ket qua cua hanh dong TRUOC (truoc day ghi lech 1 dong)
            self.nav.append((scr, act, None))
            det = screens.last_detail()
            tpl = det[0] if det else None
            if L and scr not in ("unknown", "loading"):
                L.add_sample(self.dev.idx, scr, tpl, arg[0] if arg else None, arg[1] if arg else None, img)
            if act == "done":
                if target == "world":
                    self._world_open(True)
                return True
            if scr == "unknown":
                screens.save_unknown(img, self.dev.idx, getattr(self, "step", "") or "")
                act, arg, tpl = self._learned_action(img, L, act, arg)
            self._nav_last = scr
            if stale >= 2 and act == "tap" and scr in ("city", "world"):
                # cham nut chuyen ban do 2 lan khong doi: ban do the gioi chua mo (TK dang chuoi nhiem vu dau, #3 2026-11-19)
                log.info("goto(%s): nut chuyen ban do khong co tac dung - dung", target)
                if target == "world":
                    self._world_open(False)
                return False
            if stale >= 2 and act == "tap":
                act = "back"  # cham hoai khong an thua -> Back
            if act == "tap" and L and scr in ("popup", "panel"):
                if L.dead_spot(tpl, arg[0], arg[1]):
                    ok, n = L.spot(tpl, arg[0], arg[1])
                    log.info("goto: %s @%d,%d cham %d lan chi an %d -> dung Back (hoc tu kinh nghiem)", tpl, arg[0], arg[1], n, ok)
                    act = "back"
                elif L.choose_close(scr, tpl, arg[0], arg[1]) == "back":   # H2: Thompson tap vs Back
                    log.debug("goto: %s - bandit chon phim Back", scr)
                    act = "back"
            self.nav[-1] = (scr, act, None)            # hanh dong that su (sau khi hoc / doi sang Back)
            prev = img
            if act == "tap":
                self._scr_now = scr
                self.tap(arg[0], arg[1], wait=2.5 if scr in ("city", "world") else 0.9, tpl=tpl)
            elif act == "reward":
                self.dismiss_reward()
            elif act == "wait":
                time.sleep(2.0)
            else:
                self._scr_now = scr                    # H2: thong ke phim Back theo man
                self.safe_back()
        log.warning("goto(%s): khong toi duoc sau %d lan (man cuoi %s)", target, rounds, scr)
        return False

    def _learned_action(self, img, L, act, arg):
        """Man 'unknown' (giai doan F): 1) hang xom kNN rat giong -> cham dung nut dong/quay lai cua hang xom;
        2) nut dong/quay lai 'gan khop' (0,65-0,82) -> cham thu, ket qua quyet dinh co hoc bien the khong.
        Chi nut trong learn.LEARNABLE. -> (act, arg, tpl)"""
        if not L or not (self.cfg.get("learn") or {}).get("explore", True):
            return act, arg, None
        from bot import learn, screens
        try:
            time.sleep(0.4)
            if not screens.same(img, self.dev.screencap()):
                return act, arg, None      # man dang chuyen dong (tran danh, hoat anh) -> khong hoc, khong cham thu
            pr = L.predict(img)
            if pr:
                lab, conf, sim, (tpl, x, y) = pr
                if (lab in ("popup", "panel", "exit_dialog", "dialog") and (tpl in learn.LEARNABLE or tpl == "human")
                        and x is not None
                        and conf >= 0.8 and sim >= 0.94 and not L.dead_spot(tpl, x, y)):
                    log.info("Man la giong '%s' da gap (sim %.3f, tin %.2f) -> cham %s @%d,%d", lab, sim, conf, tpl, x, y)
                    return "tap", (x, y), tpl
                if lab in ("loading", "battle") and conf >= 0.8 and sim >= 0.94:   # tran danh: dung cham, cho
                    return "wait", None, None
            near = screens.near_miss(img, self.v, learn.LEARNABLE, lo=self.cfg.get("learn", {}).get("near_lo", 0.65))
            if near:
                tpl, (x, y, sc) = near
                if not L.dead_spot(tpl, x, y):
                    t = self.v.load(tpl)
                    h, w = t.shape[:2]
                    crop = img[max(0, y - h // 2):y - h // 2 + h, max(0, x - w // 2):x - w // 2 + w].copy()
                    self._probe = (tpl, crop if crop.shape[:2] == (h, w) else None)
                    log.info("Man la: %s gan khop %.2f @%d,%d -> cham thu (hoc bien the neu dung)", tpl, sc, x, y)
                    return "tap", (x, y), tpl
        except Exception as e:
            log.debug("learned_action: %s", e)
        return act, arg, None

    def ensure_city(self):
        # G3: kiem lai thanh pho ngay sau 1 lan kiem truoc (khong co thao tac nao o giua, < nav.skip_recheck_s giay) la thua:
        # 8155/15806 ban ghi nav cu la 'done' ngay sau 'done' (reddots 4090, quests 1881) - moi lan ~1 s chup + quet popup
        win = float(self.cfg.get("nav", {}).get("skip_recheck_s", 3.0))
        seq = getattr(self.dev, "act_seq", None)
        ok = getattr(self, "_city_ok", None)
        if win > 0 and seq is not None and ok and ok[0] == seq and time.time() - ok[1] < win:
            self.nav.append(("city", "done", None))      # giu 'lost' (runner) dem dung: buoc nay van o thanh pho
            self.city_skips = getattr(self, "city_skips", 0) + 1
            return
        t0 = time.time()
        verified = self._ensure_city()
        self.city_checks = getattr(self, "city_checks", 0) + 1
        self.city_check_s = getattr(self, "city_check_s", 0.0) + (time.time() - t0)
        if verified and getattr(self.dev, "act_seq", None) is not None:
            self._city_ok = (self.dev.act_seq, time.time())      # chi nho khi goto xac nhan DUNG la thanh pho

    def _ensure_city(self):
        """-> True neu goto xac nhan o thanh pho (khong tap gi them sau close_popups)."""
        if self.cfg.get("nav", {}).get("smart", True):
            ok = self.goto("city")
            if ok or getattr(self, "_nav_last", None) in ("city", "world"):
                seq = getattr(self.dev, "act_seq", None)
                self.close_popups()
                return bool(ok) and getattr(self.dev, "act_seq", None) == seq
        self.back_out()  # cach cu (du phong)
        if self.find("common/btn_to_city"):  # dang o ban do the gioi
            self.tap_tpl("common/btn_to_city", wait=2.5, fresh=False)
        self.close_popups()
        return False

    def ensure_world(self):
        if self.cfg.get("nav", {}).get("smart", True):
            if self.goto("world") or getattr(self, "_nav_last", None) in ("city", "world"):
                self.close_popups()
                return
        self.back_out()
        if self.find("common/btn_to_world"):
            self.tap_tpl("common/btn_to_world", wait=3, fresh=False)
        self.close_popups()

    def help_and_free(self, rounds=4, use_help=True, use_free=True):
        """Bam nut tro giup lien minh / tang toc mien phi neu dang hien. A-REL-3: tuy chon truyen vao (truoc day
        moi module ghi ctx.cfg['_use_help'/'_use_free'] -> module chay sau thua huong gia tri cua module truoc)."""
        names = []
        if use_help:
            names.append("common/btn_help")
        if use_free:
            names.append("common/btn_free")
        names = [n for n in names if self.v.has(n) and n != "common/btn_free"]   # chua cat anh mau -> bo qua im lang
        from bot.badges import free_bubbles
        for _ in range(rounds):
            if use_free:
                fb = free_bubbles(self.shot())    # bong bong "Free" (nhan theo mau + chu, 2026-11-20)
                if fb:
                    log.info("Free: hoan thanh xay mien phi @%d,%d", fb[0][0], fb[0][1])
                    self.tap(fb[0][0], fb[0][1], wait=1.5)
                    self.close_popups(1)
                    continue
            if not names or not self.tap_first(names, wait=1.0):
                return

    def skip_dialogs(self, rounds=6):
        """Hoi thoai nhan vat (khung duoi co dau tam giac, vd 'Tong thu ky: Can thoa man dieu kien tien de')
        che man hinh sau khi mo man nang cap / nhiem vu -> cham de qua. -> so lan cham."""
        n = 0
        for _ in range(rounds):
            if not self.find("tutorial/dialog_next", th=0.9):
                break
            self.tap(self.W // 2, 560, wait=1.0)
            n += 1
        if n:
            log.info("Bo qua %d hoi thoai", n)
        return n

    # ---------- nhan thuong ----------
    # Khong dung nut X chung o day: se dong luon bang thu/nhiem vu dang mo.
    REWARD_CLOSERS = ["common/btn_confirm_hero", "common/btn_confirm", "common/tap_to_continue", "common/tap_to_close", "common/btn_reward_close"]

    def claim_buttons(self, roi=None, max_taps=12):
        """Bam moi nut "Nhan"/"Nhan toan bo" tren man hien tai, nhan theo MAU + CHU (bot/buttons.py) - khong can anh
        mau tung bang. Nut bam ma man khong doi -> khong bam lai. -> so lan nhan."""
        from bot import buttons, screens
        n, dead = 0, set()
        for _ in range(max_taps * 2):
            if n >= max_taps:
                break
            img = self.shot()
            todo = [b for b in buttons.claims(img, roi) if (b.x // 20, b.y // 20) not in dead]
            if not todo:
                break
            b = todo[0]
            self._exp_begin("tap", b.x, b.y, "btn:" + b.text)
            self.dev.tap(b.x, b.y)
            self._after_tap(1.0 * self.wait_scale)
            after = self.shot()
            if screens.same(img, after):
                dead.add((b.x // 20, b.y // 20))
                continue
            log.info("Nhan (nut '%s') @%d,%d", b.text, b.x, b.y)
            n += 1
            self.dismiss_reward()
        return n

    def dismiss_reward(self, rounds=3):
        """Dong bang 'Nhan duoc phan thuong' sau khi bam Nhan."""
        time.sleep(0.6)  # bang thuong con hieu ung hien ra -> doi truoc khi nhan dien
        for _ in range(rounds):
            img = self.shot()
            if self.cancel_exit(img, "dismiss_reward"):   # REWARD_CLOSERS co 'Xac nhan' - khong duoc bam tren hop thoai thoat
                continue
            hit = None
            for n in self.REWARD_CLOSERS:
                if not self.v.has(n):          # btn_reward_close la tuy chon
                    continue
                hit = self.v.find(img, n)
                if hit:
                    break
            if not hit:
                if self.v.find(img, "common/msg_reward", th=0.75):  # nen trong suot thay doi -> nguong thap hon
                    # "Chuc mung nhan duoc": khong co nut -> cham lop phu mo ben duoi khung qua
                    self.tap(self.W // 2, int(self.H * 0.62), wait=0.8)
                    continue
                return
            # tap_to_continue: chu nam tren lop phu ngoai hop thoai -> cham chinh dong chu de dong
            # (khong cham giua-duoi man hinh vi do la thanh menu cua game)
            self.tap(hit[0], hit[1], wait=0.8)

    @staticmethod
    def is_colored(img, x, y, min_sat=80):
        """Nut dang bam duoc co mau (xanh ngoc, sat ~220); nut bi khoa mau xam (sat ~0)."""
        hsv = cv2.cvtColor(img[max(0, y - 10):y + 10, max(0, x - 35):x + 35], cv2.COLOR_BGR2HSV)
        return float(hsv[..., 1].mean()) >= min_sat

    def claim_loop(self, names, max_taps=30, roi=None, th=None, active_only=True):
        """Bam lien tuc cac nut nhan (theo thu tu uu tien) cho den khi khong con nut nao.
        active_only: bo qua nut xam (cung hinh nhung chua nhan duoc)."""
        taps = 0
        blocked = set()      # nut bam vao lai mo bang khac (vd "Kich hoat VIP") -> khong bam lai
        for _ in range(max_taps * 2):
            if taps >= max_taps:
                break
            img = self.shot()
            hit = None
            for n in names:
                cands = self.v.find_all(img, n, roi=roi, th=th)
                cands = [p for p in cands if (p[0] // 20, p[1] // 20) not in blocked]
                if active_only:
                    cands = [p for p in cands if self.is_colored(img, p[0], p[1])]
                if cands:
                    hit = max(cands, key=lambda p: p[2])
                    break
            if not hit:
                break
            log.debug("nhan %s @%d,%d", n, hit[0], hit[1])
            self.tap(hit[0], hit[1], wait=1.0)
            after = self.shot()
            x = self.v.find(after, "common/btn_close", th=0.9)
            if (x and (self.cfg.get("rewards") or {}).get("use_vip_items", True) and not getattr(self, "_vip_used", False)
                    and self.v.find(after, "rewards/vip/title_activate", th=0.9)):
                # Ruong Ngay VIP -> "Kich hoat VIP": chu du an 2026-11-20 CHO PHEP dung vat pham VIP (vd "Thoi gian VIP
                # 24 tieng" -> nut "Dung"). CHI nut "Dung" (vat pham da co); KHONG BAO GIO "Den" (mua The thang).
                self._vip_used = True          # 1 lan / luot ghe
                if self.tap_tpl("rewards/vip/btn_use", wait=1.5, th=0.9):
                    log.info("Kich hoat VIP bang vat pham (Dung) -> nhan lai ruong VIP")
                    self.dismiss_reward()
                    self.tap_first(["common/btn_close"], wait=0.8, th=0.9)   # dong bang neu con
                    continue                   # bam lai "Nhan" ruong ngay VIP
            if x and not self.v.find(after, "common/msg_reward", th=0.75):
                # bam "Nhan" ma hien BANG KHAC co nut X (vd "Kich hoat VIP" khi het vat pham / tat use_vip_items,
                # chi con "Den" mua The thang) -> KHONG chon gi, dong lai, danh dau nut nay, khong tinh
                log.info("Nut %s @%d,%d mo bang khac (khong phai qua) -> dong, bo qua", n, hit[0], hit[1])
                self.tap(x[0], x[1], wait=0.8)
                blocked.add((hit[0] // 20, hit[1] // 20))
                continue
            self.dismiss_reward()
            taps += 1
        return taps

    def open_route(self, prefix, timeout=4):
        """Cham lan luot <prefix>open_1.png, open_2.png... (vd icon thu -> tab). False neu buoc dau that bai."""
        steps = self.v.list(prefix + "open_")
        if not steps:
            return False
        for i, n in enumerate(steps):
            p = self.wait_for(n, timeout=timeout if i else 2)
            if not p:
                if i == 0:
                    return False
                log.info("Khong thay buoc %s - bo qua", n)
                continue
            self.tap(p[0], p[1], wait=1.5)
        return True

    # ---------- doc "Hanh quan x/y" ----------
    def read_marches(self):
        """'Hanh quan x/y' -> (dang di, tong) | None. P3: anh chu so mdigits truoc, Tesseract/digits sau, roi khung
        'Hanh quan' vang mat tren ban do the gioi = 0 doi (bot/march_count.py)."""
        from bot import march_count
        g = self.cfg["gather"]
        img = self.shot()
        x, y, w, h = g["march_counter_roi"]
        roi = img[y:y + h, x:x + w]
        mode = g.get("ocr", "auto")
        val, src = None, None
        if mode in ("auto", "glyphs"):
            val, src = march_count.read_glyphs(img), "glyphs"
        if val is None and mode in ("auto", "tesseract"):
            val, src = self._ocr_tesseract(roi, g.get("tesseract_cmd")), "tesseract"
        if val is None and mode in ("auto", "digits"):
            val, src = self._ocr_digits(roi), "digits"
        if val is None and mode in ("auto", "tesseract"):   # #1: nguong 150 doc "4/5" thanh "4S" -> Otsu, phong 4
            from bot import ocr as _ocr
            val, src = self._parse(_ocr.text(img, (x, y, w, h), "0123456789/", scale=4)), "tesseract"
        if g.get("infer_zero", True):
            got = march_count.infer(val, march_count.header_state(self.v, img), self._known_march_total())
            if got and not val:
                src = "no_header"
                log.info("Hanh quan: khong thay khung tren ban do the gioi -> 0/%d", got[1])
            val = got
        self._march_src = src if val else None
        if val:
            log.info("Hanh quan %d/%d", *val)
            self._march = (val[0], val[1], time.time())
        return val

    def _known_march_total(self):
        c = getattr(self, "_march", None)
        if c:
            return c[1]
        st = self.store.inst(self.dev.idx) if getattr(self, "store", None) else {}
        return st.get("march_total")

    def march_full(self):
        """Het doi hanh quan? Chu du an 2026-11-21: so quan doan toi da = so hanh dong ngoai the gioi cung luc
        (phan quan, tinh bao, thu thap, tan cong/cuop deu can 1 quan doan) -> x/y day thi DUNG moi viec the gioi.
        Doc man hien tai; khong thay o "Hanh quan" -> so doc gan nhat (<15 phut) -> state.json (<20 phut)."""
        v = self.read_marches()
        if v:
            return v[0] >= v[1]
        c = getattr(self, "_march", None)
        if c and time.time() - c[2] < 900:
            return c[0] >= c[1]
        st = self.store.inst(self.dev.idx) if getattr(self, "store", None) else {}
        u, t, at = st.get("march_used"), st.get("march_total"), st.get("resources_at") or 0
        if u is not None and t and time.time() - at < 1200:
            return u >= t
        return False

    def march_sent(self):
        """Vua gui 1 quan doan ra the gioi (tinh bao, mo lien minh, phan quan, cuop) -> cong 1 vao so doc gan nhat."""
        c = getattr(self, "_march", None)
        if c:
            self._march = (min(c[0] + 1, c[1]), c[1], time.time())

    @staticmethod
    def _parse(text):
        m = re.search(r"(\d+)\s*/\s*(\d+)", text or "")
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 < b <= 10 and a <= b:
                return a, b
        return None

    def _ocr_tesseract(self, roi, cmd):
        with perf.measure("ocr_march"):
            return self._ocr_tesseract_raw(roi, cmd)

    def _ocr_tesseract_raw(self, roi, cmd):
        try:
            import pytesseract
            if cmd and os.path.exists(cmd):
                pytesseract.pytesseract.tesseract_cmd = cmd
            g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            g = cv2.resize(g, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            for img in (cv2.threshold(g, 150, 255, cv2.THRESH_BINARY)[1],
                        cv2.threshold(g, 150, 255, cv2.THRESH_BINARY_INV)[1]):
                txt = pytesseract.image_to_string(
                    img, config="--psm 7 -c tessedit_char_whitelist=0123456789/")
                v = self._parse(txt)
                if v:
                    return v
        except Exception as e:
            log.debug("tesseract loi: %s", e)
        return None

    def _ocr_digits(self, roi):
        """Doc bang anh mau so: templates/digits/0..9.png va slash.png."""
        hits = []
        for d in list("0123456789") + ["slash"]:
            if not self.v.has(f"digits/{d}"):
                continue
            for x, y, s in self.v.find_all(roi, f"digits/{d}", th=0.85, min_dist=4):
                hits.append((x, s, "/" if d == "slash" else d))
        if not hits:
            return None
        hits.sort()
        dedup = []
        for h in hits:  # bo ky tu trung vi tri, giu diem cao nhat
            if dedup and abs(h[0] - dedup[-1][0]) < 5:
                if h[1] > dedup[-1][1]:
                    dedup[-1] = h
            else:
                dedup.append(h)
        return self._parse("".join(c for _, _, c in dedup))
