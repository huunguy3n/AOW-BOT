"""Chay bot nen (luong rieng) cho giao dien web va dong lenh.

Chay LAN LUOT tung instance dang bat auto: bat may -> mo game -> cac buoc -> observe -> tat may.
Dung an toan: chi dung giua 2 buoc (khong cat ngang thao tac), may van duoc tat trong finally.
"""
import collections, logging, threading, time, traceback

from bot.device import LDConsole, Device
from bot.ctx import Ctx, Stuck
from bot import ocr
from bot.memory import Memory
from bot import scheduler
from bot.modules import tutorial, mainquest, construct, city, rewards, alliance, quests, campaign, notify, research, train, rebels, gather, daily, observe, defense, intel, reddots, play

log = logging.getLogger("aow")
# Thu tu (chu du an 2026-11-18): tan thu -> CHAM DO (thong bao, qua, nhiem vu) -> TINH BAO -> THU THAP -> phan con lai
# Thu tu chu du an chot 2026-11-21: vao game -> HET cham do, nhan qua, tinh bao -> xay dung, dao tao linh, nghien cuu
# -> (nha chinh >= rebels.min_hq_level) tan cong Phan quan tap kich, 5 luot/ngay -> gui quan thu thap -> observe.
ORDER = [("tutorial", tutorial),
         ("notify", notify), ("reddots", reddots), ("rewards", rewards), ("collect_city", city), ("daily", daily),
         ("intel", intel),
         ("mainquest", mainquest), ("construct", construct), ("quests", quests), ("train", train), ("research", research),
         ("alliance", alliance), ("campaign", campaign), ("play", play),
         ("rebels", rebels),
         ("gather", gather)]


class Stop(Exception):
    pass


class RingLog(logging.Handler):
    """Giu N dong log gan nhat cho web."""

    def __init__(self, n=400):
        super().__init__()
        self.lines = collections.deque(maxlen=n)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s", "%H:%M:%S"))

    def emit(self, record):
        self.lines.append(self.format(record))


def instance_names(ld):
    out = {}
    for line in ld.run("list2").splitlines():
        p = line.split(",")
        if len(p) > 1 and p[0].isdigit():
            out[int(p[0])] = p[1]
    return out


class Runner:
    def __init__(self, base_cfg, store, vision):
        self.base_cfg, self.store, self.vision = base_cfg, store, vision
        self.ld = LDConsole(base_cfg["ldplayer"])
        self._stop = threading.Event()
        self._wake = threading.Event()
        self.queue = collections.deque()  # instance bam "Chay ngay"
        self._busy = {}                   # idx -> luong dang chay may do (chay song song)
        self.mem = Memory()  # tri nho lau dai (A0: chi ghi de do moc chuan)
        self.thread = None
        ocr.init(base_cfg.get("gather", {}).get("tesseract_cmd"))
        # trang thai "dang chay" con sot lai tu lan tat bot giua chung -> dat lai
        for k, st in self.store.snapshot().get("instances", {}).items():
            if st.get("status") in ("running", "starting"):
                self.store.update(int(k), status="stopped", step=None,
                                  last_error="Lan chay truoc bi ngat (bot tat giua chung)")
        self.store.runner(state="stopped")
        try:
            for idx, name in instance_names(self.ld).items():
                if idx in base_cfg["instances"]:
                    self.store.update(idx, name=name)
        except Exception as e:
            log.warning("Khong doc duoc ten instance: %s", e)

    # ---------- dieu khien ----------
    @property
    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def start(self):
        if self.running:
            return
        self._stop.clear()
        n = self.mem.close_open_visits()  # luot do dang lan truoc (tien trinh bi tat) -> 'interrupted'
        if n:
            log.info("Dong %d lan ghe do dang tu lan chay truoc (interrupted)", n)
            try:   # may do runner cu bat ma chua kip tat (web khoi dong lai giua luot) -> tat, tranh chiem cho
                left = [i for i in getattr(self.mem, "open_insts", []) if i in self.ld.running()]
                for i in left:
                    log.info("Tat may #%d con bat tu luot do dang", i)
                    self.ld.quit(i)
            except Exception as e:
                log.warning("Khong tat duoc may con sot: %s", e)
        self.thread = threading.Thread(target=self._loop, daemon=True, name="runner")
        self.thread.start()
        self.store.runner(state="running", since=time.time())

    def stop(self):
        self._stop.set()
        self._wake.set()
        self.store.runner(state="stopping")

    def run_now(self, idx):
        """Auto dang chay: chen may nay len dau hang doi. Auto dang tat: chay RIENG may nay 1 luot."""
        if self.running:
            if idx not in self.queue:
                self.queue.append(idx)
            self._wake.set()
            return
        self._stop.clear()

        def once():
            self.store.runner(state="single", since=time.time())
            try:
                self.run_account(idx)
            finally:
                self.store.runner(state="stopped")
        self.thread = threading.Thread(target=once, daemon=True, name=f"once-{idx}")
        self.thread.start()

    def _check(self):
        if self._stop.is_set():
            raise Stop()

    # ---------- vong lap ----------
    # Chu du an 2026-11-20: "mo va xu ly 2 instance cung luc" -> moi may 1 luong (run_account doc lap),
    # so luong = schedule.parallel, khong vuot ldplayer.max_running (LDConsole.launch giu khoa khi bat may).
    def _parallel(self):
        cfg = self.store.cfg_for(self.base_cfg)
        p = int((cfg.get("schedule") or {}).get("parallel", 2))
        return max(1, min(p, cfg["ldplayer"].get("max_running", 2)))

    def _spawn(self, idx, **kw):
        def work():
            try:
                self.run_account(idx, **kw)
            except Exception:
                log.error("Luong may %d loi: %s", idx, traceback.format_exc())
            finally:
                self._busy.pop(idx, None)
                self._wake.set()
        th = threading.Thread(target=work, daemon=True, name=f"#{idx}")   # ten luong hien trong log
        self._busy[idx] = th
        th.start()
        # bat 2 may cung luc nang may -> lech nhau vai giay
        self._stop.wait((self.store.cfg_for(self.base_cfg).get("schedule") or {}).get("parallel_stagger_s", 20))

    def _join_all(self):
        for th in list(self._busy.values()):
            th.join()

    def _loop(self):
        log.info("Runner bat dau (%d may song song)", self._parallel())
        if self.store.cfg_for(self.base_cfg).get("schedule", {}).get("mode", "fixed") == "smart":
            return self._loop_smart()
        try:
            while not self._stop.is_set():
                t0 = time.time()
                ids = [i for i in self.base_cfg["instances"] if self.store.inst(i).get("enabled", True)]
                todo = list(ids)
                while (todo or self.queue or self._busy) and not self._stop.is_set():
                    while len(self._busy) < self._parallel() and (self.queue or todo) and not self._stop.is_set():
                        idx = self.queue.popleft() if self.queue else todo.pop(0)
                        if idx in todo:
                            todo.remove(idx)
                        if idx not in self._busy:
                            self._spawn(idx)
                    self._wake.clear()
                    if self._busy and not self._stop.is_set():
                        self._wake.wait(10)
                self._join_all()
                if self._stop.is_set():
                    break
                cfg = self.store.cfg_for(self.base_cfg)
                pause = cfg["cycle"].get("pause_between_cycles_min", 30) * 60
                self.store.runner(state="waiting", cycle_done=time.time(), next_cycle=time.time() + pause,
                                  cycle_min=round((time.time() - t0) / 60, 1))
                log.info("Xong 1 vong %d tai khoan - nghi %d phut", len(ids), pause // 60)
                self._wake.clear()
                if not (self._stop.is_set() or self.queue):  # Dung / Chay ngay bam luc dang chay: khong ngu
                    self._wake.wait(pause)  # "Chay ngay" / Dung se danh thuc som
                if not self._stop.is_set():
                    self.store.runner(state="running")
        finally:
            self._join_all()
            self.store.runner(state="stopped")
            log.info("Runner da dung")

    # ---------- vong lap theo lich (schedule.mode = smart) ----------
    def plan_visits(self, now=None):
        ids = [i for i in self.base_cfg["instances"] if self.store.inst(i).get("enabled", True)]
        return scheduler.decide(self.mem, ids, [n for n, _ in ORDER],
                                lambda i: dict(self.store.cfg_for(self.base_cfg, i)["modules"]),
                                lambda i: self.store.cfg_for(self.base_cfg, i), now)

    def _loop_smart(self):
        log.info("Lap lich theo tri nho (schedule.mode=smart)")
        try:
            while not self._stop.is_set():
                free = len(self._busy) < self._parallel()
                if self.queue and free:  # "Chay ngay": chay du moi buoc, bo qua lich
                    idx = self.queue.popleft()
                    if idx not in self._busy:
                        self._spawn(idx, why="chay ngay")
                    continue
                now = time.time()
                visits = [v for v in self.plan_visits(now) if v.idx not in self._busy]
                for v in visits:
                    self.store.update(v.idx, next_visit=v.at, next_why=v.why)
                due = [v for v in visits if v.at <= now]
                if due and free:
                    v = due[0]  # tre han lau nhat truoc
                    log.info("Lich: ghe may %d (%s) - buoc %s", v.idx, v.why, ",".join(v.steps))
                    self.store.runner(state="running")
                    self._spawn(v.idx, modules=set(v.steps) if not v.full else None, why=v.why, mode="smart")
                    continue
                cfg = self.store.cfg_for(self.base_cfg)
                nxt = min((v.at for v in visits), default=now + 900)
                wait = max(30, min(nxt - now, scheduler.sched_cfg(cfg)["idle_check_min"] * 60))
                if self._busy:
                    wait = min(wait, 15)  # may xong se danh thuc (_wake) - van xem lai lich thuong xuyen
                else:
                    self.store.runner(state="waiting", next_cycle=nxt, cycle_done=now)
                self._wake.clear()
                if not (self._stop.is_set() or self.queue):
                    self._wake.wait(wait)
        finally:
            self._join_all()
            self.store.runner(state="stopped")
            log.info("Runner da dung")

    def defend_now(self, idx):
        """Nut 'Bat khien' tren web: chay rieng may nay, chi phong thu (ep) + quan sat."""
        self._forced = getattr(self, '_forced', set()) | {idx}
        self.run_now(idx)

    @staticmethod
    def _step_limit(cfg, name):
        """Gioi han thoi gian 1 buoc (giay) theo watchdog.step_max_min / step_max_override."""
        wd = cfg.get("watchdog", {})
        m = (wd.get("step_max_override") or {}).get(name, wd.get("step_max_min", 20))
        return m * 60 if m else None

    def _wait_game(self, ctx, cfg, pkg=None):
        """Cho game vao man choi: toi thieu launch_min_wait giay, roi xem man hinh moi 2 s - thay thanh pho / ban do /
        popup / hoi thoai la lam viec ngay (truoc day ngu co dinh launch_wait 45 s). Toi da launch_wait."""
        from bot import screens
        lc = cfg["ldplayer"]
        t0, cap = time.time(), lc.get("launch_wait", 45)
        time.sleep(min(cap, lc.get("launch_min_wait", 15)))
        relaunched = False
        while time.time() - t0 < cap:
            # 2 may bat cung luc: lenh runapp den luc Android chua san sang -> game khong mo (#2, #3 2026-11-20 21:08)
            if pkg and not relaunched and not ctx.dev.app_alive(pkg):
                log.info("Game chua mo sau %.0f s -> mo lai", time.time() - t0)
                self.ld.runapp(ctx.dev.idx, pkg)
                relaunched, t0 = True, time.time()
                time.sleep(min(cap, lc.get("launch_min_wait", 15)))
                continue
            try:
                scr, _ = screens.identify(ctx.dev.screencap(tries=1), ctx.v)
            except Exception:
                scr = None
            if scr in ("city", "world", "popup", "reward", "dialog", "exit_dialog"):
                log.info("Game san sang sau %.0f s (%s)", time.time() - t0, scr)
                return
            time.sleep(2)

    def _restart_game(self, ctx, idx, pkg, cfg):
        """Ket: dung game (force-stop, KHONG xoa du lieu) -> mo lai -> dong popup."""
        self.store.update(idx, step="khoi dong lai game", watchdog_restarts=self.store.inst(idx).get("watchdog_restarts", 0) + 1)
        ctx.dev.force_stop(pkg)
        time.sleep(3)
        self.ld.runapp(idx, pkg)
        self._wait_game(ctx, cfg, pkg)
        ctx.wd_reset(300)
        ctx.close_popups(rounds=10, settle=3)

    def _backoff(self, cfg, idx, name, res, note):
        """Loi/ket lien tiep -> tam bo buoc (chi co tac dung o che do smart). warn/miss khong tinh."""
        if name == "observe":
            return
        sc = cfg.get("schedule", {})
        if res in ("err", "stuck"):
            until = self.mem.step_failed(idx, name, note, sc.get("backoff_base_min", 30), sc.get("backoff_cap_h", 6))
            log.info("Buoc %s loi -> tam bo toi %s (che do smart)", name, time.strftime("%H:%M", time.localtime(until)))
        elif res == "ok":
            self.mem.step_ok(idx, name)

    # du kien module dang ghi rai rac trong state.json -> chep sang tri nho (A1) sau moi lan ghe
    FACT_KEYS = ("hq_level", "tutorial_done", "mainquest_need_power", "mainquest_block_reason", "name",
                 "tutorial_need_power", "tutorial_wait_until")

    def _remember_facts(self, idx):
        try:
            st = self.store.inst(idx)
            for k in self.FACT_KEYS:
                if k in st:
                    self.mem.set_fact(idx, k, st[k])
        except Exception as e:
            log.warning("Khong chep duoc du kien sang tri nho: %s", e)

    @staticmethod
    def _follow_guide(ctx):
        """Sau 1 buoc: game dang hien huong dan (ban tay / V / o do) -> lam theo ngay (tutorial.follow), khong de
        chu du an phai cham tay. Tran thua da ghi nho -> khong danh (quests._battle_blocked)."""
        try:
            why = tutorial.guide_visible(ctx.v, ctx.shot())
            if not why:
                return
            from bot.modules import quests as _q
            log.info("Huong dan cua game dang hien (%s) -> lam theo", why)
            r = tutorial.follow(ctx, max_steps=15, no_battle=_q._battle_blocked(ctx))
            log.info("Lam theo huong dan: %s", r)
            ctx.ensure_city()
        except Stop:
            raise
        except Exception as e:
            log.warning("Lam theo huong dan loi: %s", e)

    def run_account(self, idx, modules=None, why=None, mode="fixed"):
        cfg = self.store.cfg_for(self.base_cfg, idx)
        enabled = dict(cfg["modules"])
        if modules is not None:
            enabled = {k: (k in modules) for k, _ in ORDER}
        st = self.store
        st.update(idx, status="starting", step="bat may", started=time.time(), last_error=None)
        log.info("===== Instance %d =====", idx)
        visit = self.mem.visit_start(idx, why=why or ("modules" if modules else "cycle"), mode=mode)
        vres = "error"
        try:
            if not self.ld.launch(idx):
                raise RuntimeError("Khong bat duoc instance")
            dev = Device(cfg["ldplayer"]["adb"], idx, (cfg.get("adb_serials") or {}).get(idx))
            if not dev.wait_ready(cfg["ldplayer"].get("boot_timeout", 120)):
                raise RuntimeError("ADB khong ket noi duoc")
            ctx = Ctx(dev, self.vision, cfg)
            ctx.store = st
            ctx.mem, ctx.visit = self.mem, visit
            ctx.wd_enabled = cfg.get("watchdog", {}).get("enabled", True)
            if (cfg.get("learn") or {}).get("watch_human", True):
                from bot.human import HumanWatch
                ctx.human = HumanWatch(ctx, cfg["ldplayer"]["adb"]).start()   # chup anh khi chu du an thao tac tay
            st.update(idx, status="running", step="mo game")
            pkg = cfg["ldplayer"].get("game_package") or dev.find_package("warpath")
            self.ld.runapp(idx, pkg)
            self._wait_game(ctx, cfg, pkg)
            ctx.close_popups(rounds=10, settle=3)
            forced = idx in getattr(self, "_forced", set())
            if forced:
                self._forced.discard(idx)
                st.update(idx, step="phong thu")
                defense.run(ctx, force=True)
                enabled = {}  # bam tay "Bat khien": chi phong thu + quan sat
            restarts = 0
            blind = 0  # so buoc lien tiep khong chup duoc man hinh (may treo du adb van 'device')
            lost = 0   # so buoc lien tiep goto() khong ve duoc thanh pho/ban do (vd canh tan thu toi den, #4 2026-11-19)
            for name, mod in ORDER + [("observe", observe)]:
                if name != "observe" and not enabled.get(name):
                    continue
                hq_ = self.mem.fact(idx, "hq_level")
                if name == "research" and hq_ is not None and hq_ < scheduler.sched_cfg(cfg)["research_hq_min"]:
                    log.info("-- Bo buoc research: nha chinh cap %s < %d (chua co Vien nghien cuu)", hq_,
                             scheduler.sched_cfg(cfg)["research_hq_min"])
                    continue
                if name == "rebels":
                    ok_, why_ = scheduler.rebels_ready(self.mem, idx, cfg)
                    if not ok_:
                        log.info("-- Bo buoc rebels: %s", why_)
                        continue
                if name == "rebels" and ctx.march_full():
                    log.info("-- Bo buoc rebels: het quan doan ranh (hanh quan day)")
                    continue
                if name in scheduler.WORLD_STEPS and not ctx.world_ready():
                    log.info("-- Bo buoc %s: ban do the gioi chua mo (nha chinh < cap %d)", name,
                             cfg.get("world", {}).get("min_hq_level", 6))
                    continue
                self._check()
                if not ctx.dev.app_alive(pkg):  # game tu thoat / bi tat giua chung -> mo lai truoc khi lam buoc ke
                    log.warning("Game khong con chay truoc buoc %s -> mo lai", name)
                    st.update(idx, game_restarts=st.inst(idx).get("game_restarts", 0) + 1)
                    self._restart_game(ctx, idx, pkg, cfg)
                st.update(idx, step=name)
                ctx.step, ctx.nav = name, []
                log.info("-- Buoc: %s", name)
                ctx.wd_reset(self._step_limit(cfg, name))
                n0, t0, m0 = len(ctx.debug_shots), time.time(), self.vision.miss_hits
                res, shot, note, ret = "ok", None, None, None
                try:
                    if defense.under_attack(ctx):  # kiem tra canh bao truoc moi buoc
                        st.update(idx, step="phong thu")
                        defense.run(ctx)
                        st.update(idx, step=name)
                    ret = mod.run(ctx)
                    if len(ctx.debug_shots) > n0:  # module tu luu anh = co cho khong on (ket, khong thay...)
                        res, shot = "warn", ctx.debug_shots[-1]
                    elif self.vision.miss_hits > m0:  # chay xong nhung co cho bo qua vi thieu anh mau
                        res, note = "miss", "thieu anh mau (python main.py --check)"
                except Stuck as e:
                    ctx.wd_reset()
                    res, note, shot = "stuck", str(e), ctx.save_debug(f"{name}_stuck")
                    log.error("Watchdog o buoc %s: %s -> khoi dong lai game", name, e)
                    st.update(idx, last_error=f"{name}: {e} (anh {shot})")
                    restarts += 1
                    st.step_result(idx, name, res, time.time() - t0, shot, note)
                    self.mem.log_run(visit, idx, name, t0, time.time() - t0, res, note)
                    self._backoff(cfg, idx, name, res, note)
                    if restarts > cfg.get("watchdog", {}).get("max_restarts", 2):
                        raise RuntimeError(f"Watchdog: khoi dong lai {restarts - 1} lan van ket - bo tai khoan nay")
                    self._restart_game(ctx, idx, pkg, cfg)
                    continue
                except Exception as e:
                    log.error("Loi o buoc %s:\n%s", name, traceback.format_exc())
                    shot = ctx.save_debug(name)
                    res, note = "err", f"{type(e).__name__}: {e}"
                    st.update(idx, last_error=f"{name}: loi (anh {shot})")
                    blind = blind + 1 if "Khong chup duoc man hinh" in str(e) else 0
                    if not blind:  # may con chup duoc -> ve thanh pho roi sang buoc ke
                        try:
                            ctx.wd_reset(120)
                            ctx.ensure_city()
                        except (Exception, Stuck):
                            pass
                else:
                    blind = 0
                st.step_result(idx, name, res, time.time() - t0, shot, note)
                self.mem.log_run(visit, idx, name, t0, time.time() - t0, res, note, ret if name != "observe" else None)
                if ctx.nav:
                    self.mem.log_nav(visit, idx, name, ctx.nav)
                if name not in ("tutorial", "mainquest", "quests", "observe") and cfg.get("guide_follow", True):
                    self._follow_guide(ctx)
                try:
                    ctx.exp_flush()   # giai doan E: kinh nghiem cham cua buoc -> memory.db + thong ke hoc
                except Exception as e:
                    log.debug("exp_flush: %s", e)
                self._backoff(cfg, idx, name, res, note)
                if ctx.nav and name not in ("tutorial", "observe"):
                    lost = 0 if any(a == "done" for _, a, _ in ctx.nav) else lost + 1
                if lost >= 3:
                    raise RuntimeError("3 buoc lien tiep khong ve duoc thanh pho (man cuoi %s) - bo luot may nay"
                                       % (ctx.nav[-1][0] if ctx.nav else "?"))
                if blind >= 2:  # lan dau thay o #2 2026-11-19: moi buoc mat ~3 phut roi loi, ca luot ~40 phut vo ich
                    raise RuntimeError("May khong phan hoi (2 buoc lien tiep khong chup duoc man hinh) - bo luot may nay")
            st.update(idx, status="idle", step=None, last_run=time.time())
            vres = "ok"
        except Stuck as e:  # watchdog luc mo game / phong thu ep (ngoai vong buoc)
            log.error("Instance %d ket: %s", idx, e)
            vres = "stuck"
            st.update(idx, status="error", step=None, last_error=f"Watchdog: {e}")
        except Stop:
            vres = "stopped"
            st.update(idx, status="stopped", step=None)
            log.info("Dung theo yeu cau o instance %d", idx)
        except Exception as e:
            log.error("Instance %d loi: %s\n%s", idx, e, traceback.format_exc())
            st.update(idx, status="error", step=None, last_error=str(e))
        finally:
            try:
                hw = getattr(locals().get("ctx"), "human", None)
                if hw:
                    hw.stop()
            except Exception:
                pass
            try:
                self.ld.quit(idx)
            except Exception:
                pass
            self._remember_facts(idx)
            self.mem.visit_end(visit, vres)
            time.sleep(5)
