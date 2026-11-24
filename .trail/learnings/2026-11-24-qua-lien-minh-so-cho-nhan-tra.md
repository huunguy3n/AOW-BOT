---
title: "Qua lien minh: so cho nhan that la so do tren tab, Co the nhan chi la tran trong ngay; nhan lap 2 tab den khi rong"
author: Trần
date: 2026-11-24
branch: p7-live-fixes
cost: { minutes: 12, tokens: 158597 }
id: l-7f390071
scope: repo
status: active
src: agent
touches:
  - ".tmp_p11_edit.py"
  - ".tmp_p11_block.py"
  - tests/legacy/test_p11_ally_gift_loop.py
  - docs/strategy/p11-report.md
  - bot/modules/alliance.py
---

## Decided
P11 (chu du an t52u 2026-11-24): bang Qua tang lien minh nhan LAP tren ca 2 tab (dac biet + thuong): nhan -> chuyen tab di roi ve (game tai lai danh sach) -> doc lai -> lap; dung khi ca 2 tab rong VA anh moi khong con so do tab. Moi duong vao (icon thanh pho, reddots, rewards, o Lien minh) qua cung mot ham.

## Tried and ruled out
Dung "Co the nhan:N" lam so qua dang cho (P7-2): live3 243 -> 200 sau khi nhan 43 qua, danh sach "Chua co qua" ma so van 200 -> do la tran nhan trong ngay. Vong cu dung sau 1 trang, qua moi den lien tuc bi bo (badge Lien minh 26 cuoi luot).

## Watch out
So trang trong cham do tab (~258,230 / ~530,230) OCR de sai (s153309 so 5 doc ra "3"); chi nhan khi >= 2 cach doc trung nhau, khong thi dung so nut Nhan dang thay. So chi de log/tien trien, quyet dinh dung dua vao Chua co qua / khong nut / khong cham do. "Co the nhan: 0" -> bo tab thuong (cham do van hien). O "Tang qua an danh" (~30,928) nam o tab dac biet, gan vung nut "Nhan toan bo" -> anh mau Nhan toan bo chi tim trong CLAIM_ALL_ROI.

In the code: bot/modules/alliance.py gift_loop / gift_count / badge_number; config alliance.gift_loop_rounds/gift_loop_max_s/gift_stall_rounds; khung data/pm-shots/owner-20261124/live3/auto/s152956, s153301-s153334.
