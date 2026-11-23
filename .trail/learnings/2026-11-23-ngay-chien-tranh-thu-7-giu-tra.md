---
title: "Ngay chien tranh thu 7: giu khien lien tuc, Hiep uoc truoc gio G roi khien tuc thi, mua kim cuong khong gioi han chi trong cua so"
author: Trần
date: 2026-11-23
branch: p6-agent-24h
cost: { minutes: 52, tokens: 754458 }
id: l-e6806767
scope: repo
status: active
replaces: l-897da153
src: agent
touches:
  - CLAUDE.md
  - docs/strategy/p6-huong-dan-chay-that.md
  - bot/modules/alliance.py
  - docs/strategy/p6-safety-audit.md
  - tests/legacy/test_p6_templates.py
  - bot/ctx.py
  - bot/modules/rebels.py
  - bot/modules/research.py
  - bot/modules/train.py
  - bot/tplcheck.py
---

## Decided
Chu du an 2026-11-23 thay luat khien 8h/12h chi vat pham: thu 7 (theo gio reset server cau hinh) la ngay chien tranh, can cu phai co khien lien tuc ca ngay. Dung moi loai khien; trong cua so chien tranh duoc mua bang kim cuong KHONG gioi han; ngoai cua so van tran 2000/ngay. Phat hien = lich tuan + cong tac tay auto/on/off + bang thong bao/banner; dau hieu chi THEM ngay, khong bot (khong chac -> giu khien). Thu 2 la ngay thu thap (gather len dau, khong giu quan doan phan quan). Phan quan van duoc phep ngay chien tranh; farm duoi HQ15 khong tham gia tap ket Co giap.
Moi vong close_popups / dismiss_reward goi ctx.cancel_exit truoc: hop thoai "Roi tro choi?" (do Back o thanh pho/ban do cua bot, nguoi choi hoac game) luon bam Huy. Truoc do dismiss_reward co common/btn_confirm trong REWARD_CLOSERS nen co the bam "Xac nhan" thoat game.

## Tried and ruled out
Dung Hiep uoc hoa binh de gia han giua ngay: no can 1h chuan bi, dung khi dang chien tranh se ho 1 gio (va co the thay khien dang chay). Chi dung truoc gio G khi con du 1h + le.

## Watch out
Dong 8h trong bang Bao Ho Chien Tranh la Hiep uoc (mien phi, khong co so luong duoi icon) - OCR so vat pham tra None. Chi bam khi OCR thay chu "Mien phi" phia tren nut. Vung OCR banner 'Giai doan N' uoc tu anh dien thoai 1179x2556, chua kiem tren may 540x960 -> banner_ocr mac dinh tat. Giu khien 24h can runner chay lien tuc: may chi ghe khi toi luot (toi da 2 may).

In the code: src/aowbot/domain/warday.py (wcfg, resolve_days, shield_plan, shield_options), bot/modules/warday.py ensure, bot/modules/defense.py peace/war_shield, policy.ShieldInputs daily_cap None, config warday.*, bang gem_ev.
Anh mau cat 23/11 tu #1: node_panel khop 0,807 voi hop thoai "Doi da du" -> nguong 0,9; btn_join khop 0,75 voi nut "+" benh vien / bang tim kiem -> nguong 0,9 + vung the tap ket; btn_research khop nut "Nghien cuu ngay" chi 0,41. Bang chi tiet node nam GIUA man (nut y~491), khong sat day -> tim tu khung bang xuong. Thanh so luong huan luyen mac dinh da toi da, khong co nut MAX.

In the code: bot/ctx.py cancel_exit, bot/modules/research.py btn_roi/PANEL_TH, bot/modules/rebels.py JOIN_TH/JOIN_ROI, tests/legacy/test_p6_templates.py (anh data/pm-shots/adb, chi local).
