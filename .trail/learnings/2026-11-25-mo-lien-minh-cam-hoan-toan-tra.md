---
title: Mo lien minh cam hoan toan khi nha chinh duoi cap 12 hoac chua biet cap
author: Trần
date: 2026-11-25
branch: p13b
cost: { minutes: 2, tokens: 56530 }
id: l-f27aeebc
scope: repo
status: active
src: agent
touches:
  - bot/modules/alliance.py
  - config.yaml
  - tests/legacy/test_p13b_ally_mine.py
  - bot/modules/gather.py
---

## Decided
Chu du an (t81u, 2026-11-25): nha chinh duoi cap 12 thi CAM thu thap mo lien minh, ca gui som lan hoan cuoi luot. Chua doc duoc cap nha chinh thi cung bo (an toan). Tu cap 12 moi ap luat doi quan ranh (>=2 gui som, 1 hoan cuoi luot).
In the code: `mine_hq_ok` trong bot/modules/alliance.py, goi o dau `ally_mine` va `ally_mine_end`; khoa `alliance.mine_min_hq: 12` trong config.yaml; cap lay qua `gather.hq_level`.

## Tried and ruled out
Chi chan trong nhanh gui som: bo, vi nhanh hoan cuoi luot (`late=True`) van gui duoc.

## Watch out
`hq_level` tra None khi state/memory chua co cap -> mo lien minh se im lang khong chay tren may do cho toi khi observe ghi cap nha chinh.
