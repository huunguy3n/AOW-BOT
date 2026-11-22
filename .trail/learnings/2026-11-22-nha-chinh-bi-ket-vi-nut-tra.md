---
title: Nha chinh bi ket vi nut Nhay dan toi cong trinh chua xay; luu ke hoach nha chinh va bo lui lich khi xay moi xong
author: Trần
date: 2026-11-22
branch: roadmap-impl
cost: { minutes: 24, tokens: 162820 }
id: l-c3884d40
scope: repo
status: active
src: agent
touches:
  - docs/strategy/session-drain-proposal.md
  - src/aowbot/domain/hqplan.py
  - bot/modules/upgrade.py
  - bot/modules/quests.py
  - bot/modules/construct.py
  - tests/unit/test_hqplan.py
  - bot/build.py
---

## Decided
- Nha chinh luu ke hoach rieng (cho tho, cho tai nguyen, khong toi duoc man nang cap). Ket qua "none" lien tiep thi lui lich 30p, 1h, 2h, toi da 4h. Buoc xay khac nhuong tho cho nha chinh chi khi tho dang ranh va farm chi co 1 tho.
- Khi buoc xay moi xay xong cong trinh, bo lui lich de thu lai nha chinh ngay.

## Tried and ruled out
- Lui lich co dinh sau "none": bo, vi cong trinh dieu kien vua duoc xay xong thi nha chinh van phai doi.
- Chan ca buoc mainquest de nhuong tho: bo, vi buoc do con danh chien dich.

## Watch out
- Tren #4 (nha chinh cap 4), "Nhay" tra "none" roi buoc xay moi xay duoc 6 cong trinh ngay sau do. Day la suy luan tu log, chua xac nhan bang anh man Nhay.
- Bot chay 60% thoi gian khong co lan ghe nao (do ngay 19-22/11), nen tho xay cac may farm thap ngoi ranh; do truoc khi sua thuat toan.
- Test legacy test_research_waits_for_hq_and_scheduler_skips dat khi chay rieng, hong khi chay ca bo.

In the code: src/aowbot/domain/hqplan.py, bot/hqplan.py, bot/modules/upgrade.py, bot/modules/construct.py, tools/measure_g0.py, docs/strategy/session-drain-proposal.md.
