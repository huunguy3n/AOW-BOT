---
title: "Bang het giai doan tan thu khi nang nha chinh len cap 8 nhan bang chu OCR va nut Xac nhan, chi xu ly trong luong nang cap"
author: Trần
date: 2026-11-27
branch: p13m
cost: { minutes: 13, tokens: 179307 }
id: l-a359d664
scope: repo
status: active
src: agent
touches:
  - bot/novice_popup.py
  - tests/legacy/test_p13m_t108_novice.py
  - bot/build.py
  - docs/strategy/p13m-report.md
---

## Decided
- Chu du an (t108u, 27/11/2026): bat dau nang nha chinh 7 -> 8 hien bang bao het giai doan tan thu: chi bam "Xac nhan" roi bam "Tang cap" (nut co dong ho) tiep; khong coi la vat can, khong dong X, khong "Tang cap ngay", khong tra phi.
- Nhan bang CA HAI: nut "Xac nhan" va chu "tan thu" phia tren nut (lech nhe duoc, khong khop "lan thu"). Chi xet trong luong nang cap, truoc khi ket luan ket qua: khong co anh that nen moi rong cho bam la them nguy co bam nham hop thoai khac.
- Luot da gap bang nay khong xet ca nut "ngay" ghi Mien phi.

## Tried and ruled out
- Them nut Xac nhan chung vao danh sach dong popup: cam, hop thoai thoat game cung co nut do.
- Dua vao mau icon kim cuong de tranh nut "Tang cap ngay": mau khong khop icon tren nut do (anh chu du an). Chot that su la chi bam nut o nua phai.

## Watch out
- Chua co anh that va chua chay live: kieu nut, vi tri chu la gia dinh. Khung dau tien bot gap duoc luu lai de doi chieu.
- close_popups, goto, tan thu khong nhan bang nay: neu bang hien muon co the bi dong bang X o cac duong do.

In the code: bot/novice_popup.py (find, confirm, NOVICE_RX, keep_frame -> logs/inv/novice_popup/); bot/build.py upgrade_here, press_upgrade_again, NOVICE_ROUNDS; tests/legacy/test_p13m_t108_novice.py; common/res_gem; docs/strategy/p13m-report.md muc 7.
