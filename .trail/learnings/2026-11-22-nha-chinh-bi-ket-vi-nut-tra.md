---
title: Nha chinh bi ket vi nut Nhay dan toi cong trinh chua xay; luu ke hoach nha chinh va bo lui lich khi xay moi xong
author: Trần
date: 2026-11-22
branch: roadmap-impl
cost: { minutes: 79, tokens: 279443 }
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
  - AGENTS.md
  - CLAUDE.md
  - bot/buttons.py
---

## Decided
- Nha chinh luu ke hoach rieng (cho tho, cho tai nguyen, khong toi duoc man nang cap). Ket qua "none" lien tiep thi lui lich 30p, 1h, 2h, toi da 4h. Buoc xay khac nhuong tho cho nha chinh chi khi tho dang ranh va farm chi co 1 tho.
- Khi buoc xay moi xay xong cong trinh, bo lui lich de thu lai nha chinh ngay.
- Sau luot ORDER, truoc observe, buoc lam duoc viec (ret > 0) mo khoa cac buoc da chay truoc no (tai nguyen, xay moi) nen chay lai 1 lan; upgrade lap toi 6 lan vi nang cap tuc thi mien phi dan chuoi dieu kien nha chinh. Toi da 8 lan chay lai, 30 phut moi lan ghe.
- ensure_city bo qua khi lan kiem truoc xac nhan dung thanh pho, khong co tap/swipe/Back o giua, trong 3 giay. Du lieu: 8155/15806 ban ghi nav la 'done' lien sau 'done'.
- Do thi man hinh da co san (screens.py, ctx.goto); khong viet lai. Tai lieu chi co G0-G3, khong co G4.

## Tried and ruled out
- Lui lich co dinh sau "none": bo, vi cong trinh dieu kien vua duoc xay xong thi nha chinh van phai doi.
- Chan ca buoc mainquest de nhuong tho: bo, vi buoc do con danh chien dich.
- Lap lai moi buoc khong gioi han: bo, vi nang cap bi chan thi tra 0 va vong dung dung luc tho ban.
- Ghi nho 'o thanh pho' theo _nav_last: bo, vi goto tra ve truoc khi cap nhat no; chi nho khi goto tra True.

## Watch out
- Tren #4 (nha chinh cap 4), "Nhay" tra "none" roi buoc xay moi xay duoc 6 cong trinh ngay sau do. Day la suy luan tu log, chua xac nhan bang anh man Nhay.
- Bot chay 60% thoi gian khong co lan ghe nao (do ngay 19-22/11), nen tho xay cac may farm thap ngoi ranh; do truoc khi sua thuat toan.
- Test legacy test_research_waits_for_hq_and_scheduler_skips dat khi chay rieng, hong khi chay ca bo.

In the code: src/aowbot/domain/hqplan.py, bot/hqplan.py, bot/modules/upgrade.py, bot/modules/construct.py, tools/measure_g0.py, docs/strategy/session-drain-proposal.md.
- Test kien truc cam bien dict o muc module trong domain: dung MappingProxyType.
- Chay cung luc toi da 2 may (config ldplayer.max_running); main.py --once bi giet bang timeout se de may chay, phai quit tay.
- Chua do lai ty le tiet kiem sau G3 tren luot day du.

In the code: src/aowbot/domain/drain.py, bot/runner.py (vong while + drain), bot/ctx.py (ensure_city, _ensure_city), bot/device.py (act_seq), config.yaml (drain:, nav.skip_recheck_s), tests/unit/test_drain.py, tests/legacy/test_ensure_city_skip.py.
