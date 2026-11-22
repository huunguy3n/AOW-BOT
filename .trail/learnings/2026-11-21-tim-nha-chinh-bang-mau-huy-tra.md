---
title: "Tim nha chinh bang mau huy hieu canh va luot camera, mau moi phai dang ky ten hien thi"
author: Trần
date: 2026-11-21
branch: roadmap-impl
cost: { minutes: 1, tokens: 1376 }
id: l-181a2984
scope: repo
status: active
src: agent
---

## Decided
Chu du an (2026-11-21): tim nha chinh bang cach luot camera quanh thanh pho va so khop mau, chi luu vai kieu nha. Mau la huy hieu canh tren mai: khop cheo giua cac cap 0.72-0.90, anh khong co nha chinh toi da 0.56, nguong 0.68. Mau dat trong nhom build/ vi bo kiem thu ten hien thi chi chap nhan nhom da khai bao.

## Tried and ruled out
Cham nhieu diem co dinh quanh (270,440): bo vi camera lech nha chinh tuy luc, co khi nam ngoai man hinh.
Mau ca toan than nha: bo vi hinh dang doi theo cap nha chinh, huy hieu thi khong doi.

## Watch out
Them mau moi phai them ten vao names.py va dung nhom co san (build/...), neu khong 2 test perception_names that bai.
Phan luot camera chua chay tren may that; chi co 2 kieu nha (cap 4 cua #2, cap 5 cua #3).

In the code: bot/modules/upgrade.py (find_hq, goto_hq, PAN_RING), templates/build/hq_emblem_*.png, src/aowbot/perception/eval/names.py, tests/legacy/test_upgrade_find_hq.py.
