"""Che do HOC MAU (chu du an 2026-11-21: "hoat dong van la tuyen tinh, tat order di. toi se lam mau thao tac o #3.
Hoc tu do va lam theo").

May co schedule.mode = 'demo' (dat tren web hoac data/settings.json):
  - KHONG nam trong vong auto / lich thong minh / agent: chi chay khi bam "Chay ngay" tren web;
  - bot bat may + mo game roi DUNG YEN: khong dong popup, khong chay buoc nao trong ORDER, khong observe;
  - HumanWatch (bot/human.py) ghi moi lan cham / keo / Back cua chu du an: anh truoc, anh sau, cho cham
    -> logs/human/<ngay>/ (nguon du lieu cho che do 'lam theo', giai doan 2);
  - ket thuc khi chu du an ngung thao tac demo.idle_min phut, qua demo.max_min phut, hoac bam Dung;
  - mac dinh KHONG tat may khi xong (demo.keep_open) - chu du an co the dang choi tiep.
"""
import logging, time

log = logging.getLogger("aow")
MODE = "demo"


FOLLOW = "follow"        # lam theo mau (bot/imitate.py) - giai doan 2


def mode_of(cfg):
    return (cfg.get("schedule") or {}).get("mode")


def is_demo(cfg):
    return mode_of(cfg) == MODE


def is_manual(cfg):
    """May hoc mau / lam theo mau: KHONG vao vong auto, chi chay khi chu du an bam tren web (thu co nguoi xem)."""
    return mode_of(cfg) in (MODE, FOLLOW)


def session(ctx, cfg, check, update=None, now=time.time, sleep=time.sleep):
    """Dung yen cho chu du an lam mau. check() nem Stop khi bam Dung; update(text) hien trang thai len web.
    -> so thao tac da ghi."""
    d = cfg.get("demo") or {}
    idle, cap = d.get("idle_min", 15) * 60, d.get("max_min", 180) * 60
    hw = getattr(ctx, "human", None)
    if hw is None:
        raise RuntimeError("Che do hoc mau can learn.watch_human = true (HumanWatch tat)")
    t0 = last = now()
    n0 = seen = hw.n
    log.info("Hoc mau: bot dung yen, ghi thao tac cua ban (dung sau %d phut khong thao tac, toi da %d phut)",
             idle // 60, cap // 60)
    while True:
        check()
        if hw.n != seen:
            seen, last = hw.n, now()
        t = now()
        if update:
            update(f"học mẫu: {seen - n0} thao tác · nghỉ {int(t - last) // 60}/{idle // 60} phút")
        if t - last >= idle:
            log.info("Hoc mau: %d phut khong thao tac -> ket thuc (%d thao tac)", idle // 60, seen - n0)
            break
        if t - t0 >= cap:
            log.info("Hoc mau: het %d phut -> ket thuc (%d thao tac)", cap // 60, seen - n0)
            break
        sleep(5)
    return seen - n0
