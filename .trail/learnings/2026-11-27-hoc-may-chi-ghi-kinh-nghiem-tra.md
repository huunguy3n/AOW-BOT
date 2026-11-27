---
title: "Hoc may chi ghi kinh nghiem; cho chet chi duoc dung khi dieu huong, cac module van cham cho chet"
author: Trần
date: 2026-11-27
branch: p7-live-fixes
cost: { minutes: 1, tokens: 61233 }
id: l-327aca33
scope: repo
status: active
src: agent
touches:
  - bot/learn.py
  - bot/ctx.py
  - tools/learn.py
---

## Decided
Chua sua gi (27/11/2026). Chu du an hoi "chua thay ML giup"; kiem tra cho thay Learner ghi du (~31k lan cham/24h, 45 cho chet) nhung ket qua chi dung trong dieu huong/dong popup. De xuat: chan cho chet o tang tap/tap_tpl (thu lai gian dan, khong chan Back/X), dem so lan chan len web. Cho chu du an duyet.

## Watch out
Mot so cho chet la loi module (vd gather/btn_recommended trung 1/514) - chan cham chi giam lan cham vo ich, van phai sua module.

In the code:
- bot/learn.py: Learner.dead_spot / choose_close / react_wait
- bot/ctx.py: dead_spot chi goi trong Ctx.goto (~L522) va Ctx._learned_action (~L544); Ctx.tap/tap_tpl khong hoi Learner
- Xem so lieu: python tools/learn.py report
