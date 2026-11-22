---
title: "Tinh bao unknown chu yeu do kiem bang qua qua som, ghim muc tieu khop nham goc duoi va man sau Tan cong chua biet; anh heal_no_target la cua su kien chua thuong"
author: Trần
date: 2026-11-22
branch: p5-chien-dau
cost: { minutes: 17, tokens: 270410 }
id: l-be7aed93
scope: repo
status: active
src: agent
touches:
  - CLAUDE.md
  - docs/product/ke-hoach-hoan-thien-bot.md
  - docs/strategy/implementation-roadmap.md
  - templates/README.md
  - bot/intel_rules.py
  - tests/legacy/test_p5_intel_rebels.py
  - tools/report_ro.py
  - bot/modules/defense.py
  - tests/legacy/test_p5_defense.py
  - bot/modules/heal.py
---

## Decided
P5 (PM 2026-11-23). Tinh bao 22/11: 64/92 ghim 'unknown'. Phan loai bang nhat ky cham (bang exp trong data/memory.db, chuoi tap sau intel/btn_go): 31 lan bam "Tan cong" roi khong nhan ra man ke (#1 nha chinh 30), 22 lan ghim muc tieu marker_fight khop nham goc trai duoi (cham 97,805), 3 khong thay ghim, 11 bang qua "Chuc mung nhan duoc". Sua: cho bang toi 3 s, tim ghim chi giua man, nhan man quan doan kieu moi (chi Xuat chinh khi du doan thang), tach ly do unknown_* + anh logs/inv/intel_*.

## Tried and ruled out
Noi rong bo do vong vang su kien chua thuong (notify.heal_targets): bat them 1/7 anh hut nhung bao nham 65/120 anh khac -> giu nguyen.

## Watch out
- 11/11 anh intel_panel_unknown khop msg_reward 0,79-0,93: anh luu SAU thoi diem kiem tra, nen "anh khop" khong co nghia luc kiem tra khop (bang con dang hien).
- Gia thuyet man sau "Tan cong" = man quan doan kieu moi va ghim giua man tim duoc muc tieu CHUA kiem duoc offline (exp khong luu anh) - xem logs/inv/intel_unknown_attack|target sau luot that.
- 42 anh heal_no_target KHONG phai buoc heal ma la notify.heal_event (su kien). Buoc heal khong luu anh nay.
- Log cu (21/11) co dong 'HH:MM:SS INFO Tinh bao: ...' khong ngay/luong -> dem phai lay ngay tu ten file.

In the code: bot/intel_rules.py (panel_kind, MARKER_ROI, parse_log), bot/modules/notify.py intel_mission, tools/report_ro.py intel_metrics.
