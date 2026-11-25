---
title: "Mo lien minh chi gui som khi con tu 2 quan doan ranh, con 1 thi hoan toi cuoi luot cung thu thap"
author: Trần
date: 2026-11-25
branch: p13b
cost: { minutes: 2, tokens: 76885 }
id: l-cf533b37
scope: repo
status: active
src: agent
touches:
  - bot/ctx.py
  - bot/modules/alliance.py
  - bot/modules/gather.py
  - bot/runner.py
  - tests/legacy/test_p13b_ally_mine.py
  - src/aowbot/domain/warday.py
---

## Decided
Chu du an (t77u/t78u, 2026-11-25): mo lien minh gui som trong buoc lien minh chi khi >= 2 quan doan ranh. Con 1 thi giu cho tinh bao/phan quan, gui cuoi luot ngay truoc gather. Khong doc duoc so quan doan thi coi la 1 ranh (khong gui som).
In the code: ctx.march_free(), alliance.mine_decision / ally_mine_end, gather.run goi ally_mine_end khi limit is None; ctx.ally_mine duoc runner dat lai moi luot.

## Tried and ruled out
Them buoc moi vao ORDER: bo, vi anh huong lich, web options va nhieu test thu tu.

## Watch out
Dau luot co the chua co so "Hanh quan" trong cache/state nen thuong roi vao nhanh hoan. Neu gather tat/bi bo qua trong luot thi mo lien minh da hoan khong duoc gui.
