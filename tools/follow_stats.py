"""P4: thong ke che do follow (tutorial.follow) va man la - CHI DOC log/anh, khong dung thiet bi.

  python tools/follow_stats.py                  # ket qua follow theo buoc goi + anh ket theo loai man
  python tools/follow_stats.py --replay         # + phat lai decide() (follow) tren anh ket cu: bao nhieu nay da co loi ra
  python tools/follow_stats.py --human          # + thao tac tay logs/human theo loai man (cham o dau, ket qua)
  python tools/follow_stats.py --since 2026-11-24   # chi log/anh tu ngay nay (so sanh truoc/sau mot lan chay that)

Loai man (bot.quest_rules + vai anh mau co san): bang_nhiem_vu, tinh_bao, ban_do, thanh_pho, chieu_mo, tuong,
bang_co_nut_quay_lai, popup_x, khac.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402

from bot import quest_rules  # noqa: E402
from bot.vision import Vision  # noqa: E402

LOG_RX = {
    "mainquest": re.compile(r"Nhiem vu chinh: follow_([a-z_]+)"),
    "quests": re.compile(r"Nhiem vu (?:chuong|tab_2_main) dong \d+ -> follow_([a-z_]+)"),
    "runner": re.compile(r"Lam theo huong dan: ([a-z_]+)"),
}
END_RX = re.compile(r"\[#(\d)\] Tan thu: (khong nhan ra man hinh|dat gioi han buoc|man la, Back)")
SHOT_RX = re.compile(r"^(\d{8})-\d{6}-i(\d)-follow_(stuck|maxsteps|lose)\.png$")


def screen_kind(v, img):
    k = quest_rules.follow_screen(v, img)
    if k == "quest_board":
        return "bang_nhiem_vu"
    if k == "intel":
        return "tinh_bao"
    if v.find(img, "recruit/title", th=0.85) or v.find(img, "recruit/tab_premium", th=0.85):
        return "chieu_mo"
    if v.find(img, "hero/title", th=0.85) or v.find(img, "hero/btn_levelup", th=0.85):
        return "tuong"
    if v.find(img, "common/btn_to_world"):
        return "thanh_pho"
    if k == "world":
        return "ban_do"
    if v.find(img, "common/btn_back"):
        return "bang_co_nut_quay_lai"
    if v.find(img, "common/btn_x_small") or v.find(img, "common/btn_x"):
        return "popup_x"
    return "khac"


def log_stats(since):
    out = collections.Counter()
    ends = collections.Counter()
    for f in sorted(glob.glob("logs/bot-*.log")):
        day = os.path.basename(f)[4:12]
        if since and day < since:
            continue
        for line in open(f, encoding="utf-8", errors="replace"):
            for who, rx in LOG_RX.items():
                m = rx.search(line)
                if m:
                    out[(who, m.group(1))] += 1
            m = END_RX.search(line)
            if m:
                ends[m.group(2)] += 1
    return out, ends


def shots(since, kinds=("stuck", "maxsteps")):
    for f in sorted(glob.glob("logs/shots/*-follow_*.png")):
        m = SHOT_RX.match(os.path.basename(f))
        if m and m.group(3) in kinds and (not since or m.group(1) >= since):
            yield f, m.group(3)


RESOLVED = ("exit", "build_fail")   # decide() moi co loi ra ro rang (thay vi cham giua / cho toi het buoc)


def replay(v, f, kind):
    """Phat lai decide() (follow) 3 nhip tren 1 anh ket. -> hanh dong cuoi cung / co loi ra khong."""
    from bot.modules import tutorial
    img = cv2.imread(f)
    st = {"follow": True}
    if kind == "maxsteps":   # anh chup luc da keo toi da ma van o che do xay
        st.update(in_build=True, drags=8)
    acts = []
    for idle in range(6 if kind == "maxsteps" else 3):
        act, _x, _y, why = tutorial.decide(v, img, idle, st)
        acts.append((act, why))
        if act in RESOLVED or (act == "tap" and not why.startswith(("man la", "dung yen"))):
            break
    return acts[-1]


def human(v, steps=None):
    ev = []
    for d in sorted(glob.glob("logs/human/2026*")):
        p = os.path.join(d, "events.jsonl")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                e = json.loads(line)
                e["dir"] = d
                ev.append(e)
    by = collections.defaultdict(list)
    for e in ev:
        if not e.get("before") or (steps and (e.get("bot_step") or "ngoai_buoc") not in steps):
            continue
        img = cv2.imread(os.path.join(e["dir"], e["before"]))
        if img is None:
            continue
        by[screen_kind(v, img)].append(e)
    return len(ev), by


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-mm-dd")
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--human", action="store_true")
    ap.add_argument("--human-steps", default="mainquest,quests", help="chi thao tac trong cac buoc nay ('' = tat ca)")
    a = ap.parse_args()
    since = a.since.replace("-", "") if a.since else None
    v = Vision("templates")
    out, ends = log_stats(since)
    print("== Ket qua follow theo buoc goi (log)")
    for (who, r), n in sorted(out.items(), key=lambda x: (x[0][0], -x[1])):
        print(f"  {who:10s} {r:22s} {n}")
    print("== Ly do dung (log):", dict(ends))
    kinds = collections.Counter()
    res = collections.Counter()
    for f, kind in (shots(since) if not a.human else ()):
        k = screen_kind(v, cv2.imread(f))
        kinds[(kind, k)] += 1
        if a.replay:
            act, why = replay(v, f, kind)
            ok = act in RESOLVED or (act == "tap" and not why.startswith(("man la", "dung yen")))
            res[(kind, "co loi ra" if ok else "van ket")] += 1
            if not ok:
                res[(kind, "van ket: " + k)] += 1
    print("== Anh follow_stuck / follow_maxsteps theo loai man")
    for (kind, k), n in kinds.most_common():
        print(f"  {kind:9s} {k:22s} {n}")
    if a.replay:
        print("== Phat lai decide() moi (follow) tren cac anh tren")
        for (kind, r), n in sorted(res.items()):
            print(f"  {kind:9s} {r:32s} {n}")
    if a.human:
        total, by = human(v, set(a.human_steps.split(",")) if a.human_steps else None)
        print(f"== Thao tac tay logs/human: {total}")
        for k, lst in sorted(by.items(), key=lambda x: -len(x[1])):
            pos = collections.Counter((e["type"], e["x"] // 40 * 40, e["y"] // 40 * 40, e.get("outcome")) for e in lst)
            print(f"  {k} ({len(lst)}): " + ", ".join(f"{t}@{x},{y}->{o} x{n}" for (t, x, y, o), n in pos.most_common(6)))


if __name__ == "__main__":
    main()
