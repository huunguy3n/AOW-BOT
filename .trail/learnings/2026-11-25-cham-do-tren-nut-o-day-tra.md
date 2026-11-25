---
title: "Cham do tren nut o day man hinh: giua-the roi xuong khoang trong duoi nut, nen thu nut so huu cham do va blacklist khi man khong doi"
author: Trần
date: 2026-11-25
branch: p13b
cost: { minutes: 2, tokens: 63671 }
id: l-22241a44
scope: repo
status: active
src: agent
touches:
  - bot/modules/notify.py
  - tests/legacy/test_p13b_cham_do_khong_doi.py
---

## Decided
Chu du an (2026-11-25): bam 1 diem 2 lan ma man khong doi = diem sai, dua vao danh sach den cua lan ghe, khong lap vo han. Dung lai TapGuard P12, khong viet he thong song song.
Cham do co 2 diem cham: giua the truoc, roi nut/icon sat cham (x-28,y+20).

## Tried and ruled out
Doan offset reddots/event_tiles la thu pham: sai. event_tiles (x-35,y+20) trung nut; thu pham that la nhanh cards trong claim_content (x-48,y+70).

## Watch out
Cham do (345,862) tren "Vao lich thi dau" -> giua-the roi (297,932) la khoang trong. Nut thap thi offset the khong dung. Giua-the van duoc thu truoc nen mat 1 lan bam vo ich moi man.
In the code: bot/modules/notify.py dot_tap_points, tap_red_dots; tests/legacy/test_p13b_cham_do_khong_doi.py.
