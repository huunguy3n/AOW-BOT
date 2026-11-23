---
title: "Thu thap luon chay cuoi luot moi ngay, ke ca thu 2 (bo quyet dinh gather len dau)"
author: Trần
date: 2026-11-23
branch: p7-live-fixes
cost: { minutes: 9, tokens: 161404 }
id: l-c7b870d2
scope: repo
status: active
src: agent
touches:
  - tests/legacy/test_warday_shield.py
  - bot/runner.py
  - src/aowbot/domain/warday.py
  - bot/gather_rules.py
  - bot/modules/gather.py
  - tests/legacy/test_priority_queues.py
---

## Decided
Chu du an 2026-11-24 (live #1): gather chay som chiem 5/5 quan doan nen cuop xe, phan quan, mo lien minh, tinh bao bi bo ("het quan doan ranh"). Gather nay LUON la buoc cuoi luot (truoc observe), moi ngay. Thu 2 (ngay thu thap) van cuoi luot nhung gui HET quan doan con lai (rebels_reserve = 0). Xa viec (drain) chay lai truoc gather, khong phai truoc observe.

## Tried and ruled out
P6 "thu 2 gather len dau" (W.gather_first): bo, vi chinh no gay ra live1 (gather 00:19 lap 5/5, sau do play/rebels/alliance deu bo).

## Watch out
Mo cap 1 'toobig' khong phai thong tin ve loai mo ma la quan doan ranh qua nho -> khong duoc ghi gather_top (truoc day ghi 1 -> chi thu cap 1 mai). Cap bat dau = max(gather_top, cap ma quan doan lon nhat cho het theo bang mine_caps).

In the code: bot/runner.py ORDER (gather cuoi) + DRAIN_AT; src/aowbot/domain/warday.py gather_last; bot/gather_rules.py fit_level/start_level/too_big_levels; bot/modules/gather.py remember_too_big.
