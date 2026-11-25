---
title: "Xe cuop co lua/khoi tren ban do bi bo qua bang mau, lua nam phia SAU xe, khong phai tren than xe"
author: Trần
date: 2026-11-25
branch: p13b
cost: { minutes: 2, tokens: 59667 }
id: l-bac699c0
scope: repo
status: active
src: agent
touches:
  - bot/modules/play.py
  - tests/legacy/test_p7_plunder.py
---

## Decided
Chu du an 2026-11-25: xe dang co lua/khoi (da bi cuop) bo qua ngay tren ban do, truoc khi cham mo popup. Nhan dien bang mau (khong template), gop vao kiem tra "dang chay" cu.

## Tried and ruled out
Dau X do cu (P7-6) khong bat duoc xe trong anh moi: o do khong co X, chi co lua vang-cam + khoi xam. Dung anh dien thoai lam template khong duoc (khac ti le ADB 540x960) nen do nguong bang mau tren anh thu ve 540 ngang.

## Watch out
Lua nam lech xuong ~55 px SAU tam than xe, ngoai o +-48 cu: vung quet phai keo xuong ~85 px. Hoa vang tren co cung mau nhung be (15-26 diem) nen can nguong >=40 diem va >=8x10. Nguong chi do tren 1 anh dien thoai; lan chay live tiep xem log "co lua" co bo nham xe sach khong.
In the code: bot/modules/play.py has_fire(), is_burning(); tests/legacy/test_p7_plunder.py (test_p13b_*).
