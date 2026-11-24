"""P9-1 (live-run-2 #1, 2026-11-24): may gia lap treo + chu du an cham tay giua luot.

1) May treo: truoc P9 screencap hong (dead) -> runner nem RuntimeError, bo CA LUOT con lai (live-run-2 treo 11:11
   o buoc quests, khien/lien minh/thu thap khong chay). Nay: kiem `ldconsole list2` -> may khong chay / ADB khong
   tra loi -> khoi dong lai MAY + game (chi quit/launch/runapp: KHONG pm clear, KHONG uninstall, KHONG xoa du lieu)
   roi chay tiep tu buoc KE TIEP. Toi da `ldplayer.recover_max` lan / luot.
2) Chu cham tay lien tiep (live-run-2: 11:00:51-11:00:57 nam lan cham trong 6 s, 11:09:35-11:10:01 hai muoi lan)
   -> bot TAM DUNG (khong giam len thao tac cua chu), chay lai khi tay yen `quiet_s` giay (toi da `max_wait_min`).

Ham thuan / lop nho khong phu thuoc adb -> test offline.
"""
import collections
import logging
import time

log = logging.getLogger("aow")

# mac dinh screencap (config ldplayer.screencap, P9-1 rut ngan tu 8/30/15): chup binh thuong ~0,4-0,6 s
SHOT_TIMEOUT_S = 5.0     # 1 lenh screencap
SHOT_BUDGET_S = 15.0     # 1 lan screencap() ke ca thu lai
RECONNECT_WAIT_S = 10.0  # do lai dia chi adb 1 lan
# -> may treo duoc phat hien sau toi da ~ 2 x 5 + 10 + 2 x 5 = 30 s (truoc P9: ~47 s, truoc P1: ~190 s)


def worst_detect_s(timeout_s=SHOT_TIMEOUT_S, max_timeouts=2, reconnect_s=RECONNECT_WAIT_S):
    """Thoi gian toi da tu lan chup hong dau tien toi khi Device.dead (2 timeout + do lai dia chi + 2 timeout)."""
    return max_timeouts * timeout_s + reconnect_s + max_timeouts * timeout_s


def recover_plan(running, adb_ok, done, max_recover):
    """Quyet dinh khi may khong chup duoc man hinh.
    running: idx co trong `ldconsole list2` (cot 5 = 1); adb_ok: getprop boot_completed tra '1';
    done: so lan da cuu trong luot nay. -> 'launch' (may da tat: bat lai), 'reboot' (dang chay nhung treo:
    quit + launch), 'give_up' (het luot cuu)."""
    if done >= max_recover:
        return "give_up"
    if not running:
        return "launch"
    return "reboot"   # dang chay ma screencap hong (ca khi adb con 'device'): man hinh/he thong treo -> khoi dong lai may


def recover_cfg(cfg):
    lc = (cfg or {}).get("ldplayer") or {}
    return {"max": int(lc.get("recover_max", 1)), "enabled": bool(lc.get("recover", True))}


class HumanPause:
    """Dem thao tac TAY cua nguoi (HumanWatch, da loc cham cua bot). >= `taps` lan trong `window_s` giay ->
    tam dung; het tam dung khi khong co thao tac nao trong `quiet_s` giay. Cau hinh `human_pause` (config.yaml)."""

    def __init__(self, taps=3, window_s=20.0, quiet_s=30.0, max_wait_s=600.0, enabled=True):
        self.taps, self.window_s, self.quiet_s = int(taps), float(window_s), float(quiet_s)
        self.max_wait_s, self.enabled = float(max_wait_s), bool(enabled)
        self.events = collections.deque(maxlen=64)
        self.active = False
        self.pauses = 0

    @staticmethod
    def from_cfg(cfg):
        hp = (cfg or {}).get("human_pause") or {}
        return HumanPause(hp.get("taps", 3), hp.get("window_s", 20), hp.get("quiet_s", 30),
                          float(hp.get("max_wait_min", 10)) * 60, hp.get("enabled", True))

    def note(self, t=None):
        """1 thao tac tay (tap / keo / phim) luc t."""
        self.events.append(time.time() if t is None else t)

    def paused(self, now=None):
        if not self.enabled:
            return False
        now = time.time() if now is None else now
        last = self.events[-1] if self.events else None
        if self.active:
            if last is None or now - last >= self.quiet_s:
                self.active = False
            return self.active
        recent = [t for t in self.events if now - t <= self.window_s]
        if len(recent) >= self.taps and last is not None and now - last < self.quiet_s:
            self.active = True
            self.pauses += 1
        return self.active

    def wait(self, why="", now=time.time, sleep=time.sleep, check=None):
        """Dang tam dung -> cho toi khi tay yen (toi da max_wait_s). -> so giay da cho (0 = khong dung).
        check(): ham Stop an toan cua runner (nem Stop neu chu bam Dung)."""
        if not self.paused(now()):
            return 0.0
        t0 = now()
        log.warning("Chu du an dang thao tac tay (%d lan / %.0f s) %s -> TAM DUNG bot, cho tay yen %.0f s",
                    len(self.events), self.window_s, why, self.quiet_s)
        while self.paused(now()) and now() - t0 < self.max_wait_s:
            if check:
                check()
            sleep(1.0)
        waited = now() - t0
        log.info("Het tam dung sau %.0f s -> bot chay tiep", waited)
        return waited
