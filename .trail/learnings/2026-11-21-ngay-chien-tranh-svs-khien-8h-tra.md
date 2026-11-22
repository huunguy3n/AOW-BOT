---
title: "Ngay chien tranh SVS: khien 8h roi 12h, cam gui quan, the luc la viec rieng"
author: Trần
date: 2026-11-21
branch: roadmap-impl
cost: { minutes: 6, tokens: 118879 }
id: l-1bc65ece
scope: repo
status: active
src: agent
touches:
  - bot/scheduler.py
  - config.yaml
---

## Decided
Chu du an 2026-11-21: nhan the luc bang cach dang nhap dung moc 0h/8h/15h UTC. Ngay chien tranh = thu 7 cua su kien SVS, nhan biet bang bang thong bao phoi hop chien tranh. Bat khien 8h luc 22h UTC thu 6, het thi 12h, sap het 12h ma chua qua ngay thi bat tiep 12h. Cam thu thap (va phan quan) trong ngay do. The luc khong lien quan khien: hai viec doc lap, chi chung lan ghe may. Khien chi dung vat pham, khong mua kim cuong (ADR-0008).
In the code: src/aowbot/domain/warday.py (luat thuan), bot/modules/warday.py, bot/scheduler.py (plan_warday, war_blocks), config.yaml muc warday.

## Tried and ruled out
Dung datetime/time trong domain: test kien truc cam, nen tinh thu trong tuan bang so ngay tu epoch (1/1/1970 la thu 5) va calendar.timegm.

## Watch out
Thieu anh mau templates/warday/notice.png va templates/defense/row_8h.png: chua co thi bot khong nhan ra bang va khong bat duoc khien 8h (khai tay warday.dates thay the). Che do agent chua biet lenh cam gui quan.
