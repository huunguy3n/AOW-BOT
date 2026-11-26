---
title: "So tho xay lay theo cau hinh tung may (farm 1, #1 = 2), tho ranh thi xay ngay sau moi buoc"
author: Trần
date: 2026-11-26
branch: p13f
cost: { minutes: 25, tokens: 496510 }
id: l-5f0aa5c3
scope: repo
status: active
replaces: l-c5621b4b
src: agent
touches:
  - bot/ctx.py
  - bot/modules/construct.py
  - bot/modules/upgrade.py
  - bot/runner.py
  - tests/legacy/test_back_guard.py
  - tests/legacy/test_p13f_builders.py
  - tests/legacy/test_p13f_transitions.py
  - tools/bench_transitions.py
  - CLAUDE.md
  - bot/build.py
---

## Decided
Chu du an (t90u, 26/11/2026, sau P13e): farm chi co 1 tho dung duoc; o thu 2 phai mua bang tien that, chi #1 da mua. So tho dung duoc = cau hinh theo may; so tong game bao chi de kep xuong. Farm 1/2 = day.
Trong mot luot auto, tho vua ranh thi xay ngay truoc moi buoc khac: doc hang cho xay sau moi buoc. Khong con giu tho / tai nguyen cho nha chinh khi tho dang ranh (thay luat giu cho cua ke hoach nha chinh ngay 22/11); chi nhuong khi tho dang ban. Nha chinh khong lam duoc ngay thi nang nha tai nguyen theo anh mau.
Chuyen tiep: tiet kiem bang cach bot khung chup thua (moi lan ~0,28 s), khong phai bang poll.

## Tried and ruled out
Lay y trong "x/y" lam so tho (P13e): sai, game bao tong 2 ca khi o 2 chua mua -> farm bi coi la con tho ranh.
Poll thay cho cho ngu duoi 0,5 s: cham hon vi mot lan chup + so khung da lau hon.
Rut khoang cach cua wait_for: loi it va de cham luc bang con truot.

## Watch out
Duong nang nha khac chi co 2 anh mau, moi kiem tren anh da luu, chua chay that. Worktree moi can chep data/owner-feedback tu cay chinh de 3 test cham do pass.
In the code: src/aowbot/domain/builders.py (effective_max, FillState), bot/runner.py (_fill_builders, with_fill), bot/build.py (quick_wait, builder_state), bot/modules/upgrade.py (other_buildings, res_candidates), bot/ctx.py (recent_frame, wait_change), tools/bench_transitions.py, docs/strategy/p13f-report.md.
