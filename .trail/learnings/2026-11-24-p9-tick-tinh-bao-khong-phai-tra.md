---
title: "P9: tick tinh bao khong phai hop dang nhat, OCR thanh nhiem vu chi phan co chu, con lan gai nhan bang anh mau"
author: Trần
date: 2026-11-24
branch: p7-live-fixes
cost: { minutes: 38, tokens: 251742 }
id: l-65725d47
scope: repo
status: active
src: agent
touches:
  - bot/steer.py
  - src/aowbot/perception/eval/names.py
  - templates/steer/README.md
  - templates/steer/block_roller.png
  - templates/steer/block_roller_fire.png
  - tests/legacy/test_p9_steer_roller.py
  - bot/intel_rules.py
  - bot/modules/intel.py
  - bot/modules/mainquest.py
  - bot/modules/notify.py
---

## Decided
- 3 lan "nhan hop qua da xong" lien tiep (live2 11:06:57-11:07:05) la nhan thuong ghim DA XONG (tick xanh), khong vi pham toi da 2 hop. Nhung moi tick truoc day giai phong 1 cho hop dang nhat -> co the gui hop thu 3; nay cho chi duoc giai phong khi tick nam dung ghim hop do (nho vi tri).
- Thanh nhiem vu chinh trong suot: nen thanh pho ben phai chu bi OCR thanh rac. Chi OCR tu x 52 toi het chu (khoang trong >= 18 cot), roi bo token rac dau/cuoi.
- Nha chinh doi skin (bi ngo Halloween): them mau theo san nha (khong theo bi ngo, co hoat anh); khong khop skin nao thi cham giua man + kiem nhan "Xuong kien truc".
- Con lan gai trong tran chay duong: nhan bang anh mau (lua che mau), khong theo mau.

## Tried and ruled out
- Mask cot chu "V>=200, S<=60, >=2 diem/cot": cat mat chu kem mo ("Tang Xuong kien truc" -> "Tan:"). Dung >=1 diem/cot.
- Mask long hon (V>=170): an sang nen thanh pho, mat tac dung.
- Mau nha chinh lech len phan bi ngo/tia tim: khop that chi 0.56-0.8, chong lan nen.

## Watch out
- logs/steer/*.jpg (khung debug 540x960) co rat nhieu khung con lan gai - nguon tot de cat mau vat can; cac duong ve debug chi o phan duoi.
- Mau Halloween nguong 0.68, nen gan nhat 0.66 (s105730) - sat; luoi an toan la kiem nhan ten.

In the code: bot/intel_rules.py Pickups.done(pos); bot/modules/mainquest.py text_extent/clean_text; bot/modules/upgrade.py TAP_DY + fallback HQ_TAP; bot/steer.py template_blocks BLOCK_TH 0.62; templates/steer/block_roller*.png
