---
title: Khung Hanh quan x/y an khi 0 doi ra ngoai nen agent van phai gui doi dau tien
author: Trần
date: 2026-11-21
branch: roadmap-impl
cost: { minutes: 7, tokens: 186975 }
id: l-ec5e271a
scope: repo
status: active
src: agent
touches:
  - bot/modules/tutorial.py
  - bot/modules/campaign.py
  - bot/runner.py
  - src/aowbot/infrastructure/legacy/actions.py
  - src/aowbot/domain/warday.py
  - bot/modules/observe.py
  - bot/modules/reddots.py
  - bot/modules/notify.py
  - bot/vision.py
  - bot/ocr.py
---

## Decided
Khi doc x/y that bai tren ban do the gioi, coi nhu 0 doi dang di neu da biet tong doi tu lan quan sat truoc; van kiem lai sau khi gui (phai len 1). Khong biet tong thi van khong gui.
Chu du an 2026-11-22: trong bang Qua (icon goc tren-phai) va Qua Chieu Mo, nut/ruong co chu "Mien phi" hoac khong ghi so tien thi bot nhan; co gia kim cuong thi khong bam. Tab con cham do cung duyet.

## Tried and ruled out
Coi "khong doc duoc x/y" la loi va thu lai: agent lap lai 6 lan tren may #1 (0/5 doi) ma khong bao gio gui duoc doi nao.
Loai han icon Qua khoi cham do (theo ADR-0008) bo sot qua mien phi ben trong.

## Watch out
Khung "Hanh quan x/y" CHI hien khi co doi dang di. Tren may khong co doi nao, doc x/y luon ra None du OCR dung. Tuong tu: man Tro giup lien minh khong dong bang phim Back, phai bam nut "<" hoac mui ten goc tren-trai.

In the code: src/aowbot/infrastructure/legacy/actions.py (_dispatch), bot/modules/observe.py (ghi chu khung x/y), bot/modules/tutorial.py (nhanh back cua follow).
Ruong nho chi bam khi OCR doc ra "Mien phi" duoi no; hang tab co the cuon ngang (tab ngoai man chua duyet). Chua chay tren may that.

In the code: bot/buttons.py CLAIM_TXT, bot/modules/reddots.py _shop_gift/_shop_page/_free_chest, bot/modules/notify.py recruit_gift.
