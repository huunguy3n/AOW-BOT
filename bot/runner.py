"""Chay bot nen (luong rieng) cho giao dien web va dong lenh.

Chay LAN LUOT tung instance dang bat auto: bat may -> mo game -> cac buoc -> observe -> tat may.
Dung an toan: chi dung giua 2 buoc (khong cat ngang thao tac), may van duoc tat trong finally.
"""
import collections, contextlib, json, logging, threading, time, traceback

from bot.device import LDConsole, Device
from bot.ctx import Ctx, Stuck
from bot import ocr
from bot.memory import Memory
from bot import perf, scheduler
from aowbot.domain import drain
from bot.modules import tutorial, mainquest, construct, city, rewards, alliance, quests, campaign, notify, research, train, rebels, gather, daily, observe, defense, intel, reddots, play, upgrade, heal, warday

log = logging.getLogger("aow")
# Thu tu (chu du an 2026-11-18): tan thu -> CHAM DO (thong bao, qua, nhiem vu) -> TINH BAO -> THU THAP -> phan con lai
# Thu tu chu du an chot 2026-11-21: vao game -> HET cham do, nhan qua, tinh bao -> xay dung, dao tao linh, nghien cuu
# -> (nha chinh >= rebels.min_hq_level) tan cong Phan quan tap kich, 5 luot/ngay -> gui quan thu thap -> observe.
# Q1 - thu tu uu tien chu du an 2026-11-21: cham do -> loi choi (mo, dau truong) -> tinh bao -> phan quan -> thu thap
# (~80 % thao tac tro choi); roi cac hang cho luon phai chay: huan luyen, xay dung, nghien cuu; cuoi: phan con lai
ORDER = [("warday", warday), ("tutorial", tutorial),
         ("notify", notify), ("reddots", reddots), ("rewards", rewards), ("collect_city", city),
         ("play", play), ("intel", intel), ("rebels", rebels), ("heal", heal), ("gather", gather),
         ("train", train), ("upgrade", upgrade), ("mainquest", mainquest), ("construct", construct), ("quests", quests),
         ("research", research),
         ("alliance", alliance), ("campaign", campaign), ("daily", daily)]


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


def _serial(cfg, idx):
    """adb_serials: {idx: 'host:port'} - khoa so (config.yaml) hoac chuoi (data/settings.json)."""
    m = cfg.get("adb_serials") or {}
    return m.get(idx) or m.get(str(idx))


def instance_names(ld):
    out = {}
    for line in ld.run("list2").splitlines():
        p = line.split(",")
        if len(p) > 1 and p[0].isdigit():
            out[int(p[0])] = p[1]
    return out


class Runner:
    def __init__(self, base_cfg, store, vision, agent=None):
        self.base_cfg, self.store, self.vision = base_cfg, store, vision
        # SCH-X: aowbot.app.agent.AgentHooks (main.py tao) - may co schedule.mode = 'agent' do agent quyet dinh
        self.agent = agent
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

    def effective_settings(self):
        """Gia tri DANG DUNG (config.yaml + settings.json trong bo nho tien trinh nay). A-REL-4: data/settings.json
        tren dia co the khac gia tri tien trinh web dang giu (2026-11-21: file ghi parallel 1, log ghi 2)."""
        cfg = self.store.cfg_for(self.base_cfg)
        sc = cfg.get("schedule") or {}
        return {"mode": sc.get("mode", "fixed"), "parallel": self._parallel(),
                "max_running": cfg["ldplayer"].get("max_running", 2),
                "wait_scale": (cfg.get("speed") or {}).get("wait_scale", 1.0)}

    def _log_settings(self):
        cur = self.effective_settings()
        if cur != getattr(self, "_last_settings", None):
            log.info("Cau hinh hieu luc: %s", " ".join(f"{k}={v}" for k, v in cur.items()))
            self._last_settings = cur

    def _loop(self):
        log.info("Runner bat dau (%d may song song)", self._parallel())
        self._log_settings()
        if self.store.cfg_for(self.base_cfg).get("schedule", {}).get("mode", "fixed") in ("smart", "agent"):
            return self._loop_smart()
        try:
            while not self._stop.is_set():
                self._log_settings()
                t0 = time.time()
                ids = self._auto_ids()
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
    def _auto_ids(self):
        """May trong vong tu dong: bat auto va KHONG o che do hoc mau (may hoc mau chi chay khi bam Chay ngay)."""
        from bot import demo
        return [i for i in self.base_cfg["instances"] if self.store.inst(i).get("enabled", True)
                and not demo.is_manual(self.store.cfg_for(self.base_cfg, i))]

    def plan_visits(self, now=None):
        ids = self._auto_ids()
        return scheduler.decide(self.mem, ids, [n for n, _ in ORDER],
                                lambda i: dict(self.store.cfg_for(self.base_cfg, i)["modules"]),
                                lambda i: self.store.cfg_for(self.base_cfg, i), now)

    def _spawn_agent(self):
        """May o che do agent co su kien den han -> 1 lan ghe agent. -> True neu da bat may."""
        for idx in self._auto_ids():
            if idx in self._busy:
                continue
            try:
                ev = self.agent.due_event(idx)
            except Exception as e:
                log.warning("Agent: khong doc duoc su kien may %d: %s", idx, e)
                continue
            if ev is not None:
                steps = self._piggyback(idx)
                log.info("Agent: ghe may %d (%s)%s", idx, ev.key, f" + buoc {','.join(steps)}" if steps else "")
                self.store.runner(state="running")
                self._spawn(idx, modules=set(steps), why=f"agent {ev.type.value}", mode="agent", agent_event=ev)
                return True
        return False

    def _piggyback(self, idx, now=None):
        """Buoc cu den han chay kem lan ghe agent (may da bat thi lam luon, khong de lan ghe sau)."""
        try:
            cfg = self.store.cfg_for(self.base_cfg, idx)
            return scheduler.piggyback_steps(self.mem, idx, [n for n, _ in ORDER], dict(cfg["modules"]), cfg,
                                             now or time.time())
        except Exception as e:
            log.warning("Khong tinh duoc buoc chay kem may %d: %s", idx, e)
            return []

    def _agent_event(self, idx):
        """Lan ghe theo lich cu cua may agent: su kien agent den han thi lam luon trong lan ghe nay."""
        if not self.agent:
            return None
        try:
            return self.agent.due_event(idx)
        except Exception as e:
            log.warning("Agent: khong doc duoc su kien may %d: %s", idx, e)
            return None

    def _loop_smart(self):
        log.info("Lap lich theo tri nho (schedule.mode=smart)")
        try:
            while not self._stop.is_set():
                self._log_settings()
                free = len(self._busy) < self._parallel()
                if self.queue and free:  # "Chay ngay": chay du moi buoc, bo qua lich
                    idx = self.queue.popleft()
                    if idx not in self._busy:
                        self._spawn(idx, why="chay ngay")
                    continue
                now = time.time()
                if free and self.agent and self._spawn_agent():
                    continue
                visits = [v for v in self.plan_visits(now) if v.idx not in self._busy]
                for v in visits:
                    self.store.update(v.idx, next_visit=v.at, next_why=v.why)
                due = [v for v in visits if v.at <= now]
                if due and free:
                    v = due[0]  # tre han lau nhat truoc
                    log.info("Lich: ghe may %d (%s) - buoc %s", v.idx, v.why, ",".join(v.steps))
                    self.store.runner(state="running")
                    self._spawn(v.idx, modules=set(v.steps) if not v.full else None, why=v.why, mode="smart",
                                agent_event=self._agent_event(v.idx))
                    continue
                cfg = self.store.cfg_for(self.base_cfg)
                nxt = min((v.at for v in visits), default=now + 900)
                if self.agent:   # may agent: thuc day dung luc su kien ke tiep (khong cho het idle_check_min)
                    nxt = min([nxt] + [t for t in (self.agent.next_at(i) for i in self.base_cfg["instances"]
                                                   if i not in self._busy) if t])
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

    @staticmethod
    def facts_to_copy(state, known, keys):
        """Du kien trong state.json can chep sang memory.db: CHI khi chua co hoac gia tri khac (A-FIX-2).
        Chep lai gia tri cu se dat seen_at = bay gio -> du lieu cu bi coi la moi (vd read_hq khong bao gio doc
        lai cap nha chinh vi 'vua thay' < 6 gio)."""
        out = {}
        for k in keys:
            if k not in state:
                continue
            v = json.loads(json.dumps(state[k], default=str))   # so sanh dang da luu (JSON)
            if k not in known or known[k] != v:
                out[k] = state[k]
        return out

    def _remember_facts(self, idx):
        try:
            for k, v in self.facts_to_copy(self.store.inst(idx), self.mem.facts(idx), self.FACT_KEYS).items():
                self.mem.set_fact(idx, k, v)
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

    def run_account(self, idx, modules=None, why=None, mode="fixed", agent_event=None):
        from bot import demo
        cfg = self.store.cfg_for(self.base_cfg, idx)
        demo_mode = demo.is_demo(cfg)
        enabled = dict(cfg["modules"])
        if modules is not None:
            enabled = {k: (k in modules) for k, _ in ORDER}
        if mode in ("smart", "agent") and (cfg.get("schedule") or {}).get("mode") == "agent":
            enabled["gather"] = False   # SCH-X: hanh quan may agent do agent lo (ke ca lan ghe 'tran an toan' du buoc)
        st = self.store
        st.update(idx, status="starting", step="bat may", started=time.time(), last_error=None)
        log.info("===== Instance %d =====", idx)
        visit = self.mem.visit_start(idx, why=why or ("modules" if modules else "cycle"), mode=mode)
        vres = "error"
        # A-MEAS-1: bo dem hieu nang cua lan ghe (cfg perf.enabled, mac dinh bat) -> bang perf theo buoc
        pf = perf.Perf() if (cfg.get("perf") or {}).get("enabled", True) else None
        perf.bind(pf)
        span = pf.span if pf else (lambda _k: contextlib.nullcontext())
        try:
            with span("_launch"):
                launched = self.ld.launch(idx)
            if not launched:
                raise RuntimeError("Khong bat duoc instance")
            dev = Device(cfg["ldplayer"]["adb"], idx, _serial(cfg, idx))
            dev.perf = pf
            with span("_adb_ready"):
                ready = dev.wait_ready(cfg["ldplayer"].get("boot_timeout", 120))
            if not ready:
                # may 'dang chay' nhung ADB offline (#4/#0 2026-11-22: 5 lan lien tiep): khoi dong lai may 1 lan
                log.warning("ADB #%d khong tra loi sau %ds - khoi dong lai may", idx, cfg["ldplayer"].get("boot_timeout", 120))
                self.ld.quit(idx)
                if self.ld.launch(idx):
                    with span("_adb_ready"):
                        ready = dev.wait_ready(cfg["ldplayer"].get("boot_timeout", 120))
            if not ready:
                raise RuntimeError("ADB khong ket noi duoc")
            ctx = Ctx(dev, self.vision, cfg)
            ctx.store = st
            ctx.mem, ctx.visit = self.mem, visit
            ctx.wd_enabled = cfg.get("watchdog", {}).get("enabled", True)
            if demo_mode or (cfg.get("learn") or {}).get("watch_human", True):
                from bot.human import HumanWatch
                ctx.human = HumanWatch(ctx, cfg["ldplayer"]["adb"]).start()   # chup anh khi chu du an thao tac tay
            st.update(idx, status="running", step="mo game")
            pkg = cfg["ldplayer"].get("game_package") or dev.find_package("warpath")
            with span("_runapp"):
                self.ld.runapp(idx, pkg)
            with span("_wait_game"):
                self._wait_game(ctx, cfg, pkg)
            if demo_mode:              # hoc mau: bot KHONG cham gi, ke ca dong popup
                ctx.wd_enabled = False   # man dung yen la binh thuong -> watchdog khong duoc nem Stuck
                st.update(idx, step="hoc mau")
                n = demo.session(ctx, cfg, self._check, lambda t: st.update(idx, step=t))
                st.update(idx, status="idle", step=None, last_run=time.time(), last_demo=n)
                vres = "ok"
                return
            try:
                warday.sniff(ctx)    # bang thong bao phoi hop chien tranh co the bi dong popup nuot -> bat truoc
            except Exception as e:
                log.debug("warday.sniff: %s", e)
            with span("_popups"):
                ctx.close_popups(rounds=10, settle=3)
            if demo.mode_of(cfg) == demo.FOLLOW:     # lam theo mau: thay ca ORDER bang thao tac hoc tu chu du an
                from bot import imitate
                ctx.wd_enabled = False
                st.update(idx, step="lam theo mau")
                index = imitate.Index(imitate.load_demos(idx), imitate.stop_feats())
                log.info("Lam theo mau: %d thao tac mau cua may #%d", len(index), idx)
                res = imitate.follow(ctx, index, cfg, self._check, lambda t: st.update(idx, step=t))
                st.update(idx, status="idle", step=None, last_run=time.time(), last_follow=res)
                vres = "ok"
                return
            if pf:
                self.mem.log_perf(visit, idx, "_start", pf.drain())
            forced = idx in getattr(self, "_forced", set())
            if forced:
                self._forced.discard(idx)
                st.update(idx, step="phong thu")
                defense.run(ctx, force=True)
                enabled = {}  # bam tay "Bat khien": chi phong thu + quan sat
            if agent_event is not None and self.agent:
                st.update(idx, step="agent")
                with span("agent"):
                    st.update(idx, agent_last=self.agent.session(ctx, idx, agent_event), agent_at=time.time())
                if pf:
                    self.mem.log_perf(visit, idx, "agent", pf.drain())
                # sau agent: cac buoc cu den han (modules) van chay - lan ghe agent khong con bo qua cham do
            restarts = 0
            blind = 0  # so buoc lien tiep khong chup duoc man hinh (may treo du adb van 'device')
            lost = 0   # so buoc lien tiep goto() khong ve duoc thanh pho/ban do (vd canh tan thu toi den, #4 2026-11-19)
            queue = list(ORDER) + [("observe", observe)]
            qi, done, rerun = 0, {}, collections.Counter()
            dcfg = cfg.get("drain") or {}
            t_visit = time.time()
            while qi < len(queue):
                name, mod = queue[qi]
                qi += 1
                if name == "observe" and dcfg.get("enabled", True) and not forced:
                    # G2: buoc lam duoc viec co the mo khoa buoc da chay truoc no -> chay lai truoc observe
                    if time.time() - t_visit < dcfg.get("max_visit_min", 30) * 60:
                        extra = drain.followups([n for n, _ in ORDER], done, enabled, dict(rerun), dcfg.get("max_extra", 8))
                        if extra:
                            log.info("Xa viec: chay lai %s (do %s vua lam duoc viec)", ",".join(extra),
                                     ",".join(k for k, v in done.items() if drain.worked(v)))
                            rerun.update(extra)
                            by = dict(ORDER)
                            queue[qi - 1:qi - 1] = [(n, by[n]) for n in extra]
                            name, mod = queue[qi - 1]
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
                if scheduler.war_blocks(self.mem, idx, name, cfg, time.time()):
                    log.info("-- Bo buoc %s: ngay chien tranh SVS (cam thu thap)", name)
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
                    with span("defense_check"):
                        attacked = defense.under_attack(ctx)
                    if attacked:  # kiem tra canh bao truoc moi buoc
                        st.update(idx, step="phong thu")
                        defense.run(ctx)
                        st.update(idx, step=name)
                    ret = mod.run(ctx)
                    done[name] = ret
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
                    if pf:
                        self.mem.log_perf(visit, idx, name, pf.drain())
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
                    with span("follow_guide"):
                        self._follow_guide(ctx)
                try:
                    ctx.exp_flush()   # giai doan E: kinh nghiem cham cua buoc -> memory.db + thong ke hoc
                except Exception as e:
                    log.debug("exp_flush: %s", e)
                if pf:
                    self.mem.log_perf(visit, idx, name, pf.drain())
                self._backoff(cfg, idx, name, res, note)
                if ctx.nav and name not in ("tutorial", "observe"):
                    lost = 0 if any(a == "done" for _, a, _ in ctx.nav) else lost + 1
                if lost >= 3:
                    raise RuntimeError("3 buoc lien tiep khong ve duoc thanh pho (man cuoi %s) - bo luot may nay"
                                       % (ctx.nav[-1][0] if ctx.nav else "?"))
                if blind >= 2:  # lan dau thay o #2 2026-11-19: moi buoc mat ~3 phut roi loi, ca luot ~40 phut vo ich
                    raise RuntimeError("May khong phan hoi (2 buoc lien tiep khong chup duoc man hinh) - bo luot may nay")
            sk, ck = getattr(ctx, "city_skips", 0), getattr(ctx, "city_checks", 0)
            if sk or ck:   # G3: do hieu qua bo kiem tra thanh pho
                avg = getattr(ctx, "city_check_s", 0.0) / ck if ck else 0.0
                log.info("G3: kiem tra thanh pho %d lan (TB %.2fs), bo qua %d lan -> tiet kiem ~%.0fs", ck, avg, sk, sk * avg)
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
                if not (demo_mode and (cfg.get("demo") or {}).get("keep_open", True)):   # hoc mau: de may mo
                    with span("_quit"):
                        self.ld.quit(idx)
            except Exception:
                pass
            if pf:
                self.mem.log_perf(visit, idx, "_end", pf.drain())
            perf.bind(None)
            self._remember_facts(idx)
            self.mem.visit_end(visit, vres)
            time.sleep(5)
