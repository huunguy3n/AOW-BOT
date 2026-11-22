---
title: Follow ket chu yeu vi bat dau tren man decide khong biet; logs/human chua ca thao tac keo cua chinh bot
author: Trần
date: 2026-11-22
branch: p4-nhiem-vu
cost: { minutes: 54, tokens: 366980 }
id: l-34898c48
scope: repo
status: active
src: agent
touches:
  - bot/build.py
  - bot/modules/observe.py
  - tests/legacy/test_p4_quests.py
  - bot/modules/mainquest.py
  - bot/modules/quests.py
  - config.yaml
  - src/aowbot/domain/hqplan.py
  - tests/unit/test_hqplan.py
  - web/options.py
  - bot/modules/tutorial.py
---

## Decided
P4 (PM 2026-11-23): 129 anh follow_stuck 18-22/11 = ban do the gioi 52 (thanh nhiem vu "Tham gia tap ket phan quan" dua ra ban do), bang nhiem vu kieu moi 38 (nut X do goc tren-phai, khong con nut dong cu o y 150), Tinh bao 24. Sua bang luat o che do follow (ra / Nhan / dong) va mainquest/quests doc chu nhiem vu (OCR) de KHONG cham nhiem vu la viec cua buoc khac.

## Tried and ruled out
Hoc chuoi keo-tha tu logs/human trong buoc mainquest/quests: 492/719 thao tac la keo 3-7 giay tu (80,860) - do la sendevent keo the cong trinh cua CHINH BOT bi bo ghi bat lai, khong phai nguoi. Loc theo dur > 2 s hoac chuoi keo dai truoc khi hoc.

## Watch out
- Anh build_blocked 22/11 (7/7) la "Tang cap thanh cong!" (nang ngay mien phi): man Tang cap van mo trang cap ke tiep nen nut Tang cap con. Truoc P4 tinh la 'blocked' -> ke hoach nha chinh lui 1 gio.
- Cham giua ban do the gioi mo menu o dat "Chuyen thanh / Chiem linh" - follow khong bao gio duoc lam vay.
- Chien dich doi man doi hinh sang "Cai dat quan doan" (Doi hinh de xuat + Chien dau do), dung anh mau play/btn_arena_*.

In the code: bot/quest_rules.py, bot/modules/tutorial.py (_follow_known), bot/modules/mainquest.py, bot/build.py (upgraded_ok), tools/follow_stats.py --replay/--human.
