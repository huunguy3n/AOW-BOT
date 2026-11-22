---
title: Ty le hang cho bo trong cu bi thoi phong vi o 1/1 va 3/3 khong doc duoc nen khong duoc ghi; doc so bang anh chu so cat tu anh that thay vi OCR
author: Trần
date: 2026-11-22
branch: p2-hang-cho
cost: { minutes: 22, tokens: 324428 }
id: l-2dfcb3e4
scope: repo
status: active
src: agent
touches:
  - CLAUDE.md
  - docs/strategy/implementation-roadmap.md
  - docs/strategy/priority-queues-plan.md
  - templates/README.md
  - tests/unit/test_perception_names.py
  - bot/modules/train.py
  - config.yaml
  - tests/legacy/test_p2_train.py
  - tests/regression/test_screen_loop_fixtures.py
  - bot/modules/research.py
---

## Decided
P2 (PM 2026-11-23): so "x/y" cot icon trai thanh pho doc bang anh chu so xam cat tu anh that (khop TM_CCOEFF_NORMED, ~1 ms) truoc, OCR bo phieu sau, cham do tren icon = con cho ranh. Tren 291 o icon trong fixtures + logs: dung 290, 1 o bi icon qua che (None, dung).

## Tried and ruled out
- Tesseract nhieu cach xu ly anh + bo phieu: hut 62/291 o, nhat la "1/1" nghien cuu (so 1 manh), "3/3" tren nen sang, "0/1" huan luyen.
- Nguong mau (V cao, S thap) de tach chu: chu khu rang cua, nen co/duong/hao quang vang lam nhieu, khong on dinh.
- Cham do lam tin hieu hai chieu: farm cap thap co luc KHONG hien cham khi hang ranh -> chi dung chieu "co cham = ranh".

## Watch out
- memory.log_queues chi ghi lan doc DUOC so. Truoc P2 cac lan "1/1"/"3/3" (ban) bi bo khoi mau, "0/1" (ranh) duoc ghi -> ty le bo trong trong report_ro (nghien cuu 71 %, huan luyen 37 %) bi thoi phong. So truoc/sau P2 phai tinh ca sai lech nay.
- Anh chu so hien chi co 0-3 (+ bien the "1b" co chan). Tong > 3 (vd huan luyen 4/4) se roi ve OCR cho toi khi cat them.

In the code: bot/queues.py (read_glyphs, resolve, GLYPH_OFF, GLYPH_TH 0.62), templates/qdigits/, tests/legacy/test_p2_queues.py, tests/regression/test_screen_loop_fixtures.py (queues2_*).
