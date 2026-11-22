---
title: "Ngay chien tranh SVS: khien 8h roi 12h, chi cam thu thap (phan quan duoc phep), the luc la viec rieng"
author: Trần
date: 2026-11-21
branch: roadmap-impl
cost: { minutes: 1, tokens: 5812 }
id: l-897da153
scope: repo
status: active
replaces: l-1bc65ece
src: agent
touches:
  - bot/scheduler.py
  - config.yaml
---

## Decided
Chu du an 2026-11-21: dang nhap dung moc 0h/8h/15h UTC de nhan the luc. Ngay chien tranh = thu 7 cua su kien SVS, nhan biet bang bang thong bao phoi hop chien tranh. Khien 8h luc 22h UTC thu 6, het thi 12h, sap het 12h ma chua qua ngay thi bat tiep 12h. CHI cam thu thap (gather); phan quan (rebels) duoc phep. The luc khong lien quan khien. Khien chi dung vat pham, khong mua kim cuong (ADR-0008).
In the code: src/aowbot/domain/warday.py (BLOCK_STEPS = ("gather",)), bot/modules/warday.py, bot/scheduler.py (plan_warday, war_blocks), config.yaml muc warday.

## Tried and ruled out
Cam ca rebels: chu du an sua lai, rebels duoc phep. Dung datetime/time trong domain: test kien truc cam, tinh thu bang so ngay tu epoch + calendar.timegm.

## Watch out
Thieu templates/warday/notice.png va templates/defense/row_8h.png (khai tay warday.dates thay the). Che do agent chua biet lenh cam thu thap.
