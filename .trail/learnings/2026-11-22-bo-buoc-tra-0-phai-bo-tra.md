---
title: "Bo buoc tra 0 phai bo ca o lich, khong chi o runner, neu khong may bi keo len moi 10 phut"
author: Trần
date: 2026-11-22
branch: p1-on-dinh-nen
cost: { minutes: 16, tokens: 279498 }
id: l-d57ce820
scope: repo
status: active
src: agent
touches:
  - bot/modules/reddots.py
  - config.yaml
  - tests/legacy/test_agent_gather_dispatch.py
  - tests/legacy/test_reddots_limits.py
  - web/options.py
  - bot/modules/campaign.py
  - bot/modules/observe.py
  - bot/runner.py
  - bot/scheduler.py
  - bot/stepgate.py
---

## Decided
P1 (PM 2026-11-23): heal/campaign/warday/mainquest co cong dieu kien + gian chu ky khi tra 0 lien tiep (bot/stepgate.py). Cong nay chay O CA HAI CHO: runner (truoc moi buoc, co biet lan ghe nay vua danh tran chua) va scheduler (decide_one/piggyback_steps).

## Watch out
- Neu chi bo buoc o runner: buoc khong chay -> bang runs khong co lan chay moi -> plan_build cua mainquest (trigger xay) tinh `at = lan chay cuoi + min_gap` luon <= now -> lich keo may len moi min_gap (10 phut) ma khong lam gi. Vi vay scheduler loai trigger da toi han cua buoc bi bo, nhung GIU hen tuong lai (vd moc the luc ke tiep cua warday) de may van duoc goi dung gio.
- heal KHONG bi bo o lich (planned_skip tra False): no phu thuoc tran trong chinh lan ghe (rebels truoc heal trong ORDER); lich khong biet dieu do.
- reddots khong dung stepgate ma tu gioi han trong module (min_interval_min / max_s) vi can 1 anh thanh pho de biet co cham do moi.
- Loi agent "'tuple' object has no attribute 'fact'" (21-22/11) la do bien tri nho `m` trong gather.run bi ghi de boi read_marches(); da doi ten mem/mv tu b5a7106. Dung dat ten bien `m` cho ca tri nho lan ket qua doc man hinh.

In the code: bot/stepgate.py (precheck, check, record, planned_skip), bot/scheduler.py decide_one, bot/runner.py run_account (stepgate.check / _idle_backoff), bot/modules/reddots.py (due, dead_until, remember). Config: stepgate.*, reddots.max_s, reddots.min_interval_min.
