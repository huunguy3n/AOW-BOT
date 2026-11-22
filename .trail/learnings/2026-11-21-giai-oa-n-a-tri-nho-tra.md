---
title: Giai đoạn A (trí nhớ + lập lịch) duyệt 2026-11-19
author: Trần
date: 2026-11-21
id: l-39807f1b
scope: repo
status: active
touches:
  - docs/product/ke-hoach-A-tri-nho-lap-lich.md
  - bot/memory.py
  - data/memory.db
  - tools/baseline.py
  - main.py
---

## Decided
Chủ dự án duyệt kế hoạch giai đoạn A (docs/product/ke-hoach-A-tri-nho-lap-lich.md) ngày 2026-11-19.
A0 code xong (bot/memory.py → data/memory.db, tools/baseline.py); đo 24 h trên #0 và #5 bắt đầu 2026-11-19 00:29 (dừng lúc 00:37 để chạy lượt web 6 máy) (`python main.py --only 0,5`).

Quyết định 2026-11-19:
- Bot chỉ bật máy khi cần **xây nhà, thu thập, nghiên cứu** (3 trigger duy nhất); mọi bước khác chạy kèm khi máy đã bật.
- Reset ngày server = 0h UTC (7h VN).
- Giữ ORDER trong một lượt (chưa phản đối).
- Trần an toàn: max_gap_min = 240 (quá 4 h không ghé thì vẫn vào 1 lần).

**Why:** chủ dự án muốn bot có trí nhớ, chỉ vào game khi có việc thật.

## Watch out
làm từng bước A0→A5, dừng chờ duyệt cuối A5. Không còn câu hỏi mở cho giai đoạn A. Xem aow-max-two-instances.

A5: owner chose keep smart 48h. Measurement window starts 2026-11-19 20:07 (first smart run 11:41-13:16 cut off when app quit). Compare with tools/baseline.py --mode smart --since 48 vs --mode fixed. Web via Claude preview dies with the app.

_From Claude Code's memory of this repo, last updated Nov 19._
