"""Chay bot nen (luong rieng) cho giao dien web va dong lenh.

Chay LAN LUOT tung instance dang bat auto: bat may -> mo game -> cac buoc -> observe -> tat may.
Dung an toan: chi dung giua 2 buoc (khong cat ngang thao tac), may van duoc tat trong finally.
"""
import collections, contextlib, json, logging, threading, time, traceback

from bot.device import LDConsole, Device
from bot.ctx import Ctx, Stuck
from bot import build, guide_tile, ocr
from bot.memory import Memory
from bot import hang, hqlevel, perf, quest_rules, queues, scheduler, stepgate, tapguard
from aowbot.domain import builders as builders_dom, drain, rollout
from aowbot.domain import warday as W
from bot.modules import expand, tutorial, mainquest, construct, city, rewards, alliance, quests, campaign, notify, research, train, rebels, gather, daily, observe, defense, intel, reddots, play, upgrade, heal, warday, mission, shield

log = logging.getLogger("aow")
# Thu tu (chu du an 2026-11-18): tan thu -> CHAM DO (thong bao, qua, nhiem vu) -> TINH BAO -> THU THAP -> phan con lai
# Thu tu chu du an chot 2026-11-21: vao game -> HET cham do, nhan qua, tinh bao -> xay dung, dao tao linh, nghien cuu
# -> (nha chinh >= rebels.min_hq_level) tan cong Phan quan tap kich, 5 luot/ngay -> gui quan thu thap -> observe.
# Q1 - thu tu uu tien chu du an 2026-11-21: cham do -> loi choi (mo, dau truong) -> tinh bao -> phan quan -> thu thap
# (~80 % thao tac tro choi); roi cac hang cho luon phai chay: huan luyen, xay dung, nghien cuu; cuoi: phan con lai
# P7-1 (chu du an 2026-11-24, live #1): gather LUON CUOI luot moi ngay (chay som chiem 5/5 quan doan -> cuop xe, phan quan,
# mo lien minh, tinh bao bi bo). Thu 2 (ngay thu thap) van cuoi nhung gui het quan doan con lai.
# P9-2 (chu du an 2026-11-24, live-run-2): khien SOM (ngay thuong, doc lap voi warday) + lien minh TRUOC cham do /
# tinh bao (live-run-2 treo 11:11 truoc khi toi khien / lien minh); gather van CUOI (W.gather_last).
ORDER = [("warday", warday), ("tutorial", tutorial), ("shield", shield), ("alliance", alliance),
         ("reddots", reddots), ("notify", notify), ("rewards", rewards), ("mission", mission), ("collect_city", city),
         ("play", play), ("intel", intel), ("rebels", rebels), ("heal", heal),
         ("train", train), ("upgrade", upgrade), ("expand", expand), ("mainquest", mainquest), ("construct", construct), ("quests", quests),
         ("research", research),
         ("campaign", campaign), ("daily", daily), ("gather", gather)]
# buoc xa viec (drain) chay lai TRUOC buoc nay (gather cuoi luot) - neu gather tat thi truoc observe
DRAIN_AT = ("gather", "observe")


def retry_after_recover(name, res, retried):
    """Ham thuan P12-6: may vua duoc cuu (treo / ScreencapError) giua buoc `name` -> thu lai buoc do 1 lan (chi khi buoc
    loi/ket, khong phai observe, chua thu lai trong lan ghe nay)."""
    return name != "observe" and res in ("err", "stuck") and name not in retried


def with_fill(rest, fill, mods):
    """Ham thuan P13f-2: chen cac buoc `fill` len dau hang doi con lai `rest` (buoc dang cho o sau duoc keo len, khong
    chay 2 lan) -> hang doi moi. Het tho giua chung -> runner tra ve `rest` tru cac buoc da chay."""
    return [(n, mods[n]) for n in fill] + [x for x in rest if x[0] not in fill]


def step_error_line(name, e):
    """P13g-2: dong loi dau tien phai co ten va noi dung loi (truoc: 'Loi o buoc observe:' trong, loi nam o
    traceback cac dong sau)."""
    return f"Loi o buoc {name}: {type(e).__name__}: {e}"


def lost_plan(lost, rescues, rescue_max):
    """Ham thuan P13g-2: `lost` buoc lien tiep khong ve duoc thanh pho -> None | 'rescue' (tu buoc thu 2, con luot
    cuu) | 'give_up' (tu buoc thu 3, het cach)."""
    if lost >= 2 and rescues < rescue_max:
        return "rescue"
    return "give_up" if lost >= 3 else None


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
        # P13h: do phan giai / DPI ky vong theo may (settings.json instances.N.ldplayer)
        self.ld = LDConsole(base_cfg["ldplayer"], lambda i: store.cfg_for(base_cfg, i).get("ldplayer"))
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
        self._t_started = time.time()
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
        # P6: tran cung 2 may (rollout.HARD_MAX_RUNNING) - config ghi lon hon cung chi 2
        return rollout.parallel_slots((cfg.get("schedule") or {}).get("parallel", 2), cfg["ldplayer"].get("max_running", 2))

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

    # ---------- P8-3: dang nhap hen gio cho ca 7 may (chu du an 2026-11-24) ----------
    TIMED_WHY = "dang nhap hen gio"

    def _timed_cfg(self, idx=None):
        return W.wcfg(self.store.cfg_for(self.base_cfg, idx).get("warday"))

    def _timed_lasts(self, ids):
        out = {}
        for i in ids:
            c = self._timed_cfg(i)
            if c["enabled"] and c["timed_login"]:
                out[i] = scheduler._fnum(self.mem.fact(i, "timed_login_at"))
        return out

    def _timed_pending(self, now=None, exclude=None):
        """May bat auto chua nhan ruong trong khung dang mo (ke ca may dang ban), sap theo idx."""
        c = self._timed_cfg()
        if not (c["enabled"] and c["timed_login"]):
            return []
        ids = [i for i in self._auto_ids() if i != exclude]
        return W.timed_login_pending(now or time.time(), self._timed_lasts(ids), c["timed_login_windows_utc"])

    def _timed_ready(self, now=None):
        """May cho nhan ma DANG RANH va chua thu qua 2 lan trong khung nay -> co the bat luot ngan."""
        now = now or time.time()
        w = W.login_window(now, self._timed_cfg()["timed_login_windows_utc"])
        tries = getattr(self, "_timed_tries", {})
        return [i for i in self._timed_pending(now) if i not in self._busy and w and tries.get((i, w[0]), 0) < 2]

    def _timed_spawn(self, now=None):
        """Khung dang mo: may cho nhan + ranh -> luot NGAN (ruong truoc, roi warday/notify/rewards neu con thoi gian).
        -> True neu da bat may."""
        now = now or time.time()
        ready = self._timed_ready(now)
        if not ready:
            return False
        i = ready[0]
        w = W.login_window(now, self._timed_cfg()["timed_login_windows_utc"])
        self._timed_tries = getattr(self, "_timed_tries", {})
        self._timed_tries[(i, w[0])] = self._timed_tries.get((i, w[0]), 0) + 1
        cfg = self.store.cfg_for(self.base_cfg, i)
        steps = [n for n in self._timed_cfg(i)["timed_login_steps"] if cfg["modules"].get(n)]
        if scheduler.builder_idle_now(self.mem, i, cfg)[0]:   # P13e-3: tho ranh -> gop xay vao luot ngan (khong cho vong sau)
            steps += [n for n in scheduler.FORCE_BUILD if cfg["modules"].get(n) and n not in steps]
        log.info("Dang nhap hen gio: ghe may %d (luot ngan: ruong -> %s), con cho %s", i, ",".join(steps) or "-",
                 ",".join(str(x) for x in ready[1:]) or "-")
        self.store.runner(state="running")
        self._spawn(i, modules=set(steps), why=self.TIMED_WHY, mode="timed")
        return True

    def _timed_report(self, now=None):
        """Khung vua dong (trong luc runner chay): may nao lo khung -> canh bao. -> [idx lo khung]."""
        now = now or time.time()
        c = self._timed_cfg()
        if not (c["enabled"] and c["timed_login"]):
            return []
        w = W.last_closed_window(now, c["timed_login_windows_utc"])
        if w is None or w[1] <= getattr(self, "_t_started", now) or getattr(self, "_timed_reported", None) == w[0]:
            return []
        self._timed_reported = w[0]
        miss = W.timed_login_missed(w[0], self._timed_lasts(self._auto_ids()))
        if miss:
            log.warning("Dang nhap hen gio: may %s LO khung %s UTC (khong nhan duoc ruong the luc)",
                        ",".join(str(i) for i in miss), time.strftime("%H:%M", time.gmtime(w[0])))
        else:
            log.info("Dang nhap hen gio: khung %s UTC du may", time.strftime("%H:%M", time.gmtime(w[0])))
        return miss

    def _timed_wait_cap(self, now, wait):
        """Ngu khong qua luc mo khung ke tiep (vong fixed nghi 30 phut co the trum dau khung)."""
        s = W.next_window_start(now, self._timed_cfg()["timed_login_windows_utc"])
        return wait if s is None else max(1.0, min(wait, s - now + 1))

    def _timed_due(self, idx, cfg):
        return scheduler.timed_login_due(self.mem, idx, cfg, time.time())

    def _timed_claim(self, ctx, idx, cfg):
        """Nhan ruong "Dang nhap hen gio" NGAY (dau luot ngan / buoc ke tiep cua luot dai). Chua qua delay dau khung
        -> cho toi luc do. Ghi fact timed_login_at (1 lan / khung; buoc notify van quet tab Hoat dong lan nua)."""
        c = W.wcfg(cfg.get("warday"))
        now = time.time()
        w = W.login_window(now, c["timed_login_windows_utc"])
        if w is None:
            return 0
        wait = w[0] + c["timed_login_delay_min"] * 60 - now
        if wait > 0:
            self._stop.wait(min(wait, 300))
        self._check()
        n = 0
        try:
            n = notify.timed_login_chest(ctx)
        except Exception as e:   # khong lam hong luot ghe
            log.warning("Dang nhap hen gio may %d: loi %s", idx, e)
            try:
                ctx.ensure_city()
            except Exception:
                pass
        self.mem.set_fact(idx, "timed_login_at", time.time())
        log.info("Dang nhap hen gio may %d (khung %s UTC): %s", idx, time.strftime("%H:%M", time.gmtime(w[0])),
                 "da nhan ruong" if n else "khong thay ruong (notify se quet lai)")
        return n

    def effective_settings(self):
        """Gia tri DANG DUNG (config.yaml + settings.json trong bo nho tien trinh nay). A-REL-4: data/settings.json
        tren dia co the khac gia tri tien trinh web dang giu (2026-11-21: file ghi parallel 1, log ghi 2)."""
        cfg = self.store.cfg_for(self.base_cfg)
        sc = cfg.get("schedule") or {}
        return {"mode": sc.get("mode", "fixed"), "parallel": self._parallel(),
                "max_running": rollout.max_running(cfg["ldplayer"].get("max_running", 2)),
                "agent": "bat" if rollout.agent_switch(cfg) else "tat",
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
                while (todo or self.queue or self._busy or self._timed_ready()) and not self._stop.is_set():
                    self._timed_report()
                    while (len(self._busy) < self._parallel() and (self.queue or todo or self._timed_ready())
                           and not self._stop.is_set()):
                        if not self.queue and self._timed_spawn():   # P8-3: khung Dang nhap hen gio -> luot ngan truoc
                            continue
                        if not (self.queue or todo):
                            break
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
                    self._wake.wait(self._timed_wait_cap(time.time(), pause))  # P8-3: thuc dung dau khung hen gio
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
                self._timed_report(now)
                if free and self._timed_spawn(now):   # P8-3: khung Dang nhap hen gio -> luot ngan cho may chua nhan
                    continue
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
                wait = self._timed_wait_cap(now, wait)
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

    def _builder_idle_now(self, ctx):
        """So tho dung duoc dang ranh (doc hang cho xay tren thanh pho) -> (ranh, (dang xay, tong)) | (None, None)."""
        ctx.wd_reset(120)            # ngoai vong buoc: dung de gioi han gio cua buoc truoc danh Stuck
        recent = getattr(ctx, "recent_frame", None)
        idle, b = build.builder_state(ctx, recent(1.0) if recent else None)
        if b is None:
            ctx.ensure_city()
            idle, b = build.builder_state(ctx)
        if b is not None:
            self.mem.set_fact(ctx.dev.idx, "builders_busy", b[0])
        return idle, b

    def _fill_builders(self, ctx, cfg, allowed, fs, t_visit, after, ret):
        """P13f-2: sau buoc `after` (tra `ret`) - tho RANH -> ten cac buoc xay can chay NGAY truoc buoc ke (hoac [])."""
        if time.time() - t_visit > (cfg.get("drain") or {}).get("max_visit_min", 30) * 60 + 600:
            return []
        try:
            idle, b = self._builder_idle_now(ctx)
            if b is None:
                return []
            gained = (after not in builders_dom.FILL_STEPS and drain.worked(ret)
                      and "upgrade" in drain.UNLOCKS.get(after, ()))
            if not fs.decide(b[0], idle, getattr(ctx, "builds_started", 0), gained):
                return []
        except (Exception, Stuck) as e:   # khong de loi doc hang cho lam hong luot ghe
            log.warning("Tho ranh: loi %s", e)
            return []
        steps = [n for n in builders_dom.FILL_STEPS if allowed.get(n)]
        if steps:
            log.info("Tho ranh sau buoc %s: %d/%d dang xay, con %d ranh -> xay NGAY (%s) [lan %d]", after, b[0], b[1],
                     idle, ",".join(steps), fs.rounds)
        return steps

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
            if getattr(ctx.dev, "dead", False):   # A-OPT-3: may treo -> khong cho het launch_wait
                raise RuntimeError("May khong phan hoi luc mo game (khong chup duoc man hinh) - bo luot may nay")
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

    def _recover_device(self, ctx, idx, pkg, cfg, done, name):
        """P9-1: may treo (screencap hong ca sau khi do lai dia chi). ldconsole list2 -> may khong chay: bat lai;
        dang chay ma treo: quit + launch. Roi cho ADB, mo game, dong popup. KHONG pm clear / uninstall / xoa du lieu.
        -> True neu may chup duoc man hinh tro lai (runner chay tiep buoc ke tiep)."""
        rc = hang.recover_cfg(cfg)
        if not rc["enabled"]:
            return False
        try:
            running = idx in self.ld.running()
        except Exception as e:
            log.warning("Cuu may #%d: ldconsole list2 loi %s", idx, e)
            running = True
        plan = hang.recover_plan(running, None, done, rc["max"])
        log.warning("May #%d treo o buoc %s (list2: %s) -> %s", idx, name, "dang chay" if running else "KHONG chay",
                    {"launch": "bat lai may", "reboot": "khoi dong lai may (khong xoa du lieu)",
                     "give_up": f"het luot cuu ({done}/{rc['max']})"}[plan])
        if plan == "give_up":
            return False
        st = self.store
        st.update(idx, step="khoi dong lai may treo", device_recovers=st.inst(idx).get("device_recovers", 0) + 1)
        try:
            if plan == "reboot":
                self.ld.quit(idx)
            if not self.ld.launch(idx):
                log.error("Cuu may #%d: khong bat lai duoc", idx)
                return False
            boot = cfg["ldplayer"].get("boot_timeout", 120)
            if not ctx.dev.wait_ready(boot):
                log.error("Cuu may #%d: ADB khong tra loi sau %d s", idx, boot)
                return False
            ctx.dev.dead = False
            self.ld.runapp(idx, pkg)
            self._wait_game(ctx, cfg, pkg)
            ctx.wd_reset(300)
            ctx.close_popups(rounds=10, settle=3)
            ctx.shot()
        except (Exception, Stuck) as e:
            log.error("Cuu may #%d that bai: %s", idx, e)
            return False
        log.info("May #%d da chay lai sau khi treo -> tiep tuc (buoc %s: thu lai 1 lan neu chua thu)", idx, name)
        return True

    def _rescue_city(self, ctx, idx, pkg, cfg):
        """P13g-2: ket (khong ve duoc thanh pho) -> thu lan luot, dung o cach dau tien thanh cong: 1) Huy hop thoai
        thoat + dong popup roi di lai (goto lo phim Back / nut quay lai / ban do -> thanh pho); 2) khoi dong lai GAME
        (force-stop, KHONG xoa du lieu). -> True neu da o thanh pho."""
        ways = (("dong popup roi di lai", lambda: ctx.close_popups(rounds=6, settle=2)),
                ("khoi dong lai game", lambda: self._restart_game(ctx, idx, pkg, cfg)))
        for label, act in ways:
            try:
                ctx.wd_reset(300)
                log.warning("Cuu ket #%d: %s", idx, label)
                act()
                if ctx.goto("city", rounds=8):
                    log.info("Cuu ket #%d: da ve thanh pho (%s)", idx, label)
                    return True
            except (Exception, Stuck) as e:
                log.warning("Cuu ket #%d: %s loi %s: %s", idx, label, type(e).__name__, e)
        return False

    def _final_try(self, ctx, label, fn):
        """P13g-2: viec phu cuoi luot (khien / nhan qua / quet cham do) loi KHONG duoc lan sang buoc observe.
        May da khong chup duoc man hinh -> bo qua. -> ket qua cua fn | None."""
        if getattr(ctx.dev, "dead", False):
            return None
        try:
            return fn()
        except Exception as e:
            log.warning("%s: loi %s: %s", label, type(e).__name__, e)
        if not getattr(ctx.dev, "dead", False):
            try:
                ctx.ensure_city()
            except Exception as e:
                log.warning("%s: sau loi khong ve duoc thanh pho: %s: %s", label, type(e).__name__, e)
        return None

    def _recover_after_final(self, ctx, idx, pkg, cfg, done, name):
        """P13g-2 (#1 26/11 10:55): ADB hong luc quet cham do cuoi luot -> cuu may TRUOC roi van chay buoc `name`
        (observe) -> 1 neu da cuu duoc, 0 neu khong (buoc se loi va di theo duong P9-1 nhu cu)."""
        log.warning("May #%d khong chup duoc man hinh o viec cuoi luot -> cuu may truoc buoc %s", idx, name)
        return int(bool(self._recover_device(ctx, idx, pkg, cfg, done, name)))

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

    def _idle_backoff(self, cfg, idx, name, res, ret):
        """P1: buoc tra 0 lien tiep -> gian chu ky (bot.stepgate, luu fact idle:<buoc> theo may + state.json)."""
        try:
            until = stepgate.record(self.mem, idx, name, res, ret, cfg)
            if until:
                log.info("Buoc %s tra 0 %d lan lien tiep -> gian chu ky toi %s", name,
                         stepgate.idle_state(self.mem, idx, name).get("zeros", 0),
                         time.strftime("%H:%M", time.localtime(until)))
            self.store.update(idx, idle_backoff=stepgate.snapshot(self.mem, idx, cfg))
        except Exception as e:   # tri nho loi khong duoc lam hong lan ghe
            log.warning("stepgate: %s", e)

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
            if k == "hq_level" and hqlevel.lowers(v, known.get(k)):
                continue        # P13i: chep state -> tri nho khong duoc ha cap nha chinh (bot/hqlevel.py)
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
            recent = getattr(ctx, "recent_frame", None)
            img = recent(0.6) if recent else None
            why = tutorial.guide_visible(ctx.v, img if img is not None else ctx.shot(), guide_tile.blocked_by(ctx))
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
        # --modules tren dong lenh (why None) = chu du an muon chay dung buoc do -> khong qua stepgate
        explicit = modules is not None and why is None
        if mode in ("smart", "agent") and rollout.agent_active(cfg):
            enabled["gather"] = False   # SCH-X: hanh quan may agent do agent lo (ke ca lan ghe 'tran an toan' du buoc)
        short = mode == "timed"         # P8-3: luot NGAN trong khung Dang nhap hen gio
        tcfg = W.wcfg(cfg.get("warday"))
        t_visit0 = time.time()
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
            dev = Device(cfg["ldplayer"]["adb"], idx, _serial(cfg, idx)).configure(cfg["ldplayer"])
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
                if not demo_mode:   # P9-1: chu cham tay lien tiep -> tam dung (hoc mau: bot von khong cham gi)
                    ctx.human_pause = hang.HumanPause.from_cfg(cfg)
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
            if short or (not forced and self._timed_due(idx, cfg)):
                st.update(idx, step="dang nhap hen gio")
                with span("timed_login"):
                    self._timed_claim(ctx, idx, cfg)   # P8-3: ruong "Dang nhap hen gio" DAU TIEN
            restarts = 0
            recovers = 0  # P9-1: so lan da khoi dong lai may treo trong luot nay
            blind = 0  # so buoc lien tiep khong chup duoc man hinh (may treo du adb van 'device')
            lost = 0   # so buoc lien tiep goto() khong ve duoc thanh pho/ban do (vd canh tan thu toi den, #4 2026-11-19)
            rescues = 0  # P13g-2: so lan da cuu ket (dong popup / khoi dong lai game) trong luot nay
            queue = list(ORDER) + [("observe", observe)]
            if (cfg.get("priority") or {}).get("idle_first", True) and not forced and not short:
                try:   # o rong (tho 0/2, nghien cuu 0/1, huan luyen x/3) -> lam truoc (chu du an 2026-11-22)
                    ctx.ensure_city()
                    qs0 = queues.read(self.vision, ctx.shot(), observe.known_totals(ctx))
                    bq0 = qs0.get("build")
                    idle0 = drain.idle_slots(qs0, build.max_builders(ctx, bq0[1] if bq0 else None))   # P13e-1
                    if idle0:
                        names = drain.prioritize([n for n, _ in ORDER], idle0, enabled)
                        by0 = dict(ORDER)
                        queue = [(n, by0[n]) for n in names] + [("observe", observe)]
                        log.info("Uu tien o rong %s: chay truoc %s", ",".join(idle0), ",".join(names[:6]))
                except Exception as e:   # khong de doc hang cho lam hong luot ghe
                    log.warning("Uu tien o rong: loi %s", e)
            byq = dict(queue)
            queue = [(n, byq[n]) for n in W.gather_last([n for n, _ in queue])]   # P7-1: gather luon cuoi luot
            if enabled.get("gather") and warday.gather_day(cfg) and not forced:
                log.info("Ngay thu thap: gather cuoi luot, gui het quan doan con lai")
            off = [n for n, _ in ORDER if not enabled.get(n) and n != "tutorial"]
            if off and not forced:   # P7-5: buoc tat trong cai dat may -> ghi ro (live #1: quests tat, bo qua im lang)
                log.info("Buoc dang tat (cai dat may / config): %s", ",".join(off))
            ctx.quests_claim_only = False
            if not short and quest_rules.quests_mode(bool(enabled.get("quests")), cfg.get("quests"),
                                                     forced or explicit) == "claim":
                enabled["quests"] = True        # P7-5: tat 'quests' = khong xay theo "Den", van nhan thuong nhiem vu
                ctx.quests_claim_only = True
                log.info("Buoc quests tat -> chi nhan thuong nhiem vu (quests.claim_when_off)")
            qi, done, rerun = 0, {}, collections.Counter()
            retried = set()           # P12-6: buoc da thu lai sau khi cuu may treo
            drained = False
            # P13f-2: sau MOI buoc, tho ranh -> chen cac buoc xay truoc buoc ke (ke ca buoc khong nam trong luot lich)
            bc = cfg.get("build") or {}
            fill_state = builders_dom.FillState(int(bc.get("fill_rounds", 8)), int(bc.get("fill_retries", 2)))
            fill_on = bool(bc.get("fill_idle", True)) and not short and not forced
            fill_allowed = {n: bool(enabled.get(n) if explicit else cfg["modules"].get(n))
                            and self.mem.backoff_until(idx, n) <= time.time() for n in builders_dom.FILL_STEPS}
            if ctx.quests_claim_only:
                fill_allowed["quests"] = False
            last_ran, block, final_done = None, None, False   # block: lan chen dang chay (xem with_fill)
            ctx.visit_done = done   # reddots: biet buoc nao vua chay xong ma khong lam duoc gi
            ctx.ally_mine = None   # P13b: None | 'deferred' (hoan cuoi luot) | 'sent' | 'done'
            ctx.visit_kinds = set()   # P13-2: viec reddots da xu ly trong lan ghe nay (rewards / mission khong lam lai)
            ctx.tap_guard = tapguard.TapGuard()   # P12-2: toa do cham 2 lan vo hieu -> danh sach den trong lan ghe
            dcfg = cfg.get("drain") or {}
            t_visit = time.time()
            while qi < len(queue):
                if last_ran is not None and fill_on:
                    nxt = queue[qi][0]
                    if block and nxt in block[0]:   # dang trong lan chen: het tho ranh -> tra hang doi ve thu tu cu
                        try:
                            full = self._builder_idle_now(ctx)[0] == 0
                        except (Exception, Stuck) as e:
                            log.warning("Tho ranh: loi %s", e)
                            full = False
                        if full:
                            ran = block[2] - block[0]
                            queue[qi:] = [x for x in block[1] if x[0] not in ran]
                            block, last_ran = None, None
                            continue
                    elif nxt not in drain.HEAD and nxt not in builders_dom.FILL_STEPS:
                        fill = self._fill_builders(ctx, cfg, fill_allowed, fill_state, t_visit, *last_ran)
                        if fill:
                            block = (set(fill), queue[qi:], frozenset(fill))
                            queue[qi:] = with_fill(queue[qi:], fill, dict(ORDER))
                            enabled = {**enabled, **dict.fromkeys(fill, True)}
                last_ran = None
                name, mod = queue[qi]
                qi += 1
                if not short and name != "observe" and not forced and self._timed_due(idx, cfg):
                    # P8-3: may dang chay luot dai khi khung mo -> nhan ruong NGAY o buoc ke tiep
                    st.update(idx, step="dang nhap hen gio")
                    with span("timed_login"):
                        self._timed_claim(ctx, idx, cfg)
                    others = self._timed_ready()      # may khac dang CHO luong (ranh, chua nhan)
                    if tcfg["timed_login_yield"] and W.timed_login_yield(time.time(), tcfg["timed_login_windows_utc"],
                                                                         len(others)):
                        log.info("Dang nhap hen gio: may %s con cho -> ket thuc luot som, nhuong luong (bo %s)",
                                 ",".join(str(i) for i in others), ",".join(n for n, _ in queue[qi - 1:] if n != "observe"))
                        queue[qi - 1:] = [("observe", observe)]
                        name, mod = queue[qi - 1]
                        drained = True                 # khong xa viec them - nhuong luong ngay
                        fill_on = False
                if short and name != "observe" and time.time() - t_visit0 > tcfg["timed_login_visit_max_min"] * 60:
                    log.info("-- Bo buoc %s: luot ngan dang nhap hen gio da qua %d phut", name,
                             tcfg["timed_login_visit_max_min"])
                    continue
                if name in DRAIN_AT and not drained and dcfg.get("enabled", True) and not forced and not short:
                    drained = True
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
                if block:
                    block[0].discard(name)
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
                if not forced and not explicit:
                    g_ = stepgate.check(self.mem, idx, name, cfg, time.time(), done)
                    if not g_.run:   # P1: dieu kien truoc khi chay / gian chu ky khi tra 0 lien tiep
                        log.info("-- Bo buoc %s: %s", name, g_.why)
                        continue
                self._check()
                ctx.human_gate(f"truoc buoc {name}")   # P9-1: chu dang thao tac tay -> cho
                if not ctx.dev.app_alive(pkg):  # game tu thoat / bi tat giua chung -> mo lai truoc khi lam buoc ke
                    log.warning("Game khong con chay truoc buoc %s -> mo lai", name)
                    st.update(idx, game_restarts=st.inst(idx).get("game_restarts", 0) + 1)
                    self._restart_game(ctx, idx, pkg, cfg)
                st.update(idx, step=name)
                ctx.step, ctx.nav = name, []
                log.info("-- Buoc: %s", name)
                ctx.wd_reset(self._step_limit(cfg, name))
                n0, t0, m0 = len(ctx.debug_shots), time.time(), self.vision.miss_hits
                res, shot, note, ret, seq0 = "ok", None, None, None, None
                try:
                    with span("defense_check"):
                        attacked = defense.under_attack(ctx)
                    if attacked:  # kiem tra canh bao truoc moi buoc
                        st.update(idx, step="phong thu")
                        defense.run(ctx)
                        done["defense"] = 1   # P5-3: lan ghe co bi danh -> heal bat buoc (stepgate.FIGHT_STEPS)
                        st.update(idx, step=name)
                    ctx.visit_pending = {n for n, _ in queue[qi:]}   # P10-5: reddots de cham do cho buoc con cho
                    final, claimed_end = name == "observe" and not short and not forced and not final_done, None
                    if final and enabled.get("shield"):
                        # P10-7: khien CUOI luot - tat / con < 1h -> gia han (dau luot da chay buoc shield)
                        with span("shield_end"):
                            log.info("Khien cuoi luot: kiem lai")
                            self._final_try(ctx, "Khien cuoi luot", lambda: shield.run(ctx))
                    if final and enabled.get("reddots", True):
                        # P10-5: nhan qua cuoi luot (thu bao cao moi, qua lien minh, chieu mo) truoc observe
                        with span("final_claims"):
                            claimed_end = self._final_try(ctx, "Nhan qua cuoi luot",
                                                          lambda: reddots.final_claims(ctx))
                        if reddots.rcfg(cfg)["final_sweep"]:
                            # P13d-1: quet lai 1 vong cham do cuoi luot (bo qua tan suat + tri nho vo ich)
                            with span("reddots_final"):
                                swept = self._final_try(ctx, "Quet cham do cuoi luot",
                                                        lambda: reddots.run(ctx, final=True))
                            claimed_end = swept or claimed_end
                    if final and getattr(ctx.dev, "dead", False):
                        # P13g-2 (#1 26/11 10:55): ADB hong luc quet cham do -> cuu may TRUOC roi van quan sat
                        recovers += self._recover_after_final(ctx, idx, pkg, cfg, recovers, name)
                    if final:
                        final_done = True
                        # P13f-2: nhan qua cuoi luot mat vai phut -> cong trinh ngan da xong: xay tiep roi moi observe
                        fill = (self._fill_builders(ctx, cfg, fill_allowed, fill_state, t_visit, "reddots", claimed_end)
                                if fill_on else [])
                        if fill:
                            rest = [(name, mod)] + queue[qi:]
                            block = (set(fill), rest, frozenset(fill))
                            queue[qi:] = with_fill(rest, fill, dict(ORDER))
                            enabled = {**enabled, **dict.fromkeys(fill, True)}
                            continue
                        ctx.wd_reset(self._step_limit(cfg, name))
                    seq0 = getattr(ctx.dev, "act_seq", None)
                    if name in builders_dom.FILL_STEPS and not (name == "quests" and ctx.quests_claim_only):
                        fill_state.attempt(getattr(ctx, "builds_started", 0))
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
                    log.error("%s\n%s", step_error_line(name, e), traceback.format_exc())
                    shot = ctx.save_debug(name)
                    res, note = "err", f"{type(e).__name__}: {e}"
                    st.update(idx, last_error=f"{name}: {note} (anh {shot})")
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
                if getattr(ctx.dev, "dead", False) or blind >= 2:
                    # A-OPT-3: ADB/screencap khong cuu duoc (da do lai dia chi). P9-1: thu khoi dong lai MAY + game
                    # (ldconsole list2 -> launch/reboot; KHONG pm clear) roi chay tiep buoc KE TIEP; het luot cuu -> bo may
                    if pf:
                        self.mem.log_perf(visit, idx, name, pf.drain())
                    if self._recover_device(ctx, idx, pkg, cfg, recovers, name):
                        recovers += 1
                        blind = lost = 0
                        if retry_after_recover(name, res, retried):
                            # P12-6 (live4 #2: upgrade 0 % - ScreencapError, may treo, khoi dong lai, bo buoc): lam lai
                            # DUNG 1 lan buoc dang do
                            retried.add(name)
                            queue.insert(qi, (name, mod))
                            log.warning("May #%d chay lai sau treo -> THU LAI buoc %s (1 lan)", idx, name)
                        continue
                    raise RuntimeError(f"May khong phan hoi o buoc {name} (khong chup duoc man hinh) - bo luot may nay")
                if ctx.nav:
                    self.mem.log_nav(visit, idx, name, ctx.nav)
                # P13f-3: buoc khong cham / vuot gi -> man khong the hien huong dan moi: bo kiem (~1,5 s/lan)
                touched = seq0 is None or getattr(ctx.dev, "act_seq", None) != seq0
                if (touched and name not in ("tutorial", "mainquest", "quests", "observe") and cfg.get("guide_follow", True)
                        and not (name == "intel" and notify.intel_stopped(ctx))):   # P13j: buoc Tinh bao da dung
                    with span("follow_guide"):
                        self._follow_guide(ctx)
                try:
                    ctx.exp_flush()   # giai doan E: kinh nghiem cham cua buoc -> memory.db + thong ke hoc
                except Exception as e:
                    log.debug("exp_flush: %s", e)
                if pf:
                    self.mem.log_perf(visit, idx, name, pf.drain())
                self._backoff(cfg, idx, name, res, note)
                self._idle_backoff(cfg, idx, name, res, ret)
                last_ran = (name, ret)
                if ctx.nav and name not in ("tutorial", "observe"):
                    lost = 0 if any(a == "done" for _, a, _ in ctx.nav) else lost + 1
                plan = lost_plan(lost, rescues, int((cfg.get("nav") or {}).get("rescue_max", 1)))
                if plan and name != "observe":
                    last_scr = ctx.nav[-1][0] if ctx.nav else "?"
                    if plan == "rescue":
                        rescues += 1
                        log.warning("%d buoc lien tiep khong ve duoc thanh pho (man cuoi %s) -> cuu ket [lan %d]",
                                    lost, last_scr, rescues)
                        if self._rescue_city(ctx, idx, pkg, cfg):
                            lost = 0
                        elif not getattr(ctx.dev, "dead", False):   # may treo: buoc ke se cuu may (P9-1)
                            plan = "give_up"
                    if plan == "give_up":
                        raise RuntimeError("%d buoc lien tiep khong ve duoc thanh pho (man cuoi %s), da cuu %d lan - "
                                           "bo luot may nay" % (lost, last_scr, rescues))
                # (blind >= 2: lan dau thay o #2 2026-11-19 - P9-1 xu ly cung cho voi Device.dead o tren)
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
