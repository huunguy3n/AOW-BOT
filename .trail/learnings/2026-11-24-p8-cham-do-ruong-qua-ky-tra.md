---
title: "P8: cham do ruong Qua ky dieu toi hon cham thuong, doc luc chien ta sau Doi hinh de xuat, va khung Dang nhap hen gio dung luot ngan de du 7 may"
author: Trần
date: 2026-11-24
branch: p7-live-fixes
cost: { minutes: 24, tokens: 326526 }
id: l-a70fe777
scope: repo
status: active
src: agent
touches:
  - CLAUDE.md
  - bot/modules/quests.py
  - bot/quest_rules.py
  - tests/legacy/test_p8_quests_main.py
  - bot/modules/notify.py
  - bot/runner.py
  - config.yaml
  - src/aowbot/domain/warday.py
  - tests/legacy/test_p8_timed_login_7.py
  - bot/modules/play.py
---

## Decided
- Cuop xe (chu du an 2026-11-24, lan thua ho ve 243.560.931 > ta 222.749.681): chi bam "Chien dau" khi doc duoc CA HAI so va ho ve < ta (va ta >= ho ve x (1 + loot.power_margin)). Luc chien ta doc SAU khi bam "Doi hinh de xuat" vi doi hinh de xuat doi luc chien; truoc P8 bot doc truoc khi bam.
- Khung Dang nhap hen gio 1 gio la du cho 7 may NEU luot ghe trong khung la luot ngan (ruong truoc, <= 12 phut): 7 may / 2 luong = 4 dot = 48 phut. Luot day du ~19 phut thi khong du (chi ~6 may).
- May dang chay luot dai khi khung mo: nhan ruong o buoc ke tiep, roi ket thuc som neu con may khac dang cho luong (timed_login_yield).
- Nhiem vu: dong "mua / nap / kim cuong / goi qua / tan cong nguoi choi / can cu" la nhom CAM, khong bao gio bam "Den" (ca mainquest).

## Tried and ruled out
- Dung red_dots (badges) cho cham do ruong mien phi Qua ky dieu: tren anh ADB #1 cham do do H~8, V 130-170 nen red_dots (H<=6, V>=190) khong thay -> ruong khong bao gio duoc nhan. Thay bang mission.chest_dot do rieng o hop canh ruong.

## Watch out
- play/item_crystal cung khop icon pha le tren the Loi choi (~314,182): chi tim trong CRYSTAL_ROI cua popup xe.
- ally/tab_territory khop 0.92 ca khi tab dang chon, khong dung de biet tab nao dang mo.
- Anh ADB goc de test o data/pm-shots/owner-20261124/p8-adb (gitignore) -> test tu skip khi thieu.
- Chua kiem tren may that: vung OCR luc chien ta (68,360) chi doi chieu tren 1 fixture; khong doc duoc thi bot luu anh loot_own_power va bo xe.

In the code: bot/modules/play.py power_check/own_power/guard_power, bot/modules/mission.py chest_dot, bot/runner.py _timed_* (mode="timed"), src/aowbot/domain/warday.py simulate_waves/timed_login_pending, bot/quest_rules.py FORBIDDEN; config loot.power_margin, loot.max_attempts, warday.timed_login_visit_max_min/steps/yield.
