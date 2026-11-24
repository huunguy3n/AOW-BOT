---
title: "P10: popup cuop xet theo nut khong theo toast, chieu mo lam tab hien tai truoc, o Cap can bam OK ban phim, cham do tien trinh dai de buoc rieng"
author: Trần
date: 2026-11-24
branch: p7-live-fixes
cost: { minutes: 32, tokens: 334478 }
id: l-a6585f20
scope: repo
status: active
src: agent
touches:
  - bot/modules/shield.py
  - bot/runner.py
  - config.yaml
  - tests/legacy/test_p10_shield_renew.py
  - bot/modules/notify.py
  - tests/legacy/test_p10_welfare.py
  - bot/modules/alliance.py
  - bot/modules/reddots.py
  - bot/modules/rewards.py
  - tests/legacy/test_p10_reddots.py
---

## Decided
- Cuop xe: popup ban do la popup cuop khi co nut "Cuop boc" ben phai (+ SR/SSR); toast "Da chuyen doi sang sv ServerID" chi tinh khi KHONG co nut (live3 15:39:09 bo nham xe SSR dung). Loc som: chua biet luc doi -> ho ve >= TONG luc chien tai khoan thi bo (luc doi <= tong).
- Chieu mo: loi "khong thay luot mien phi" (~30 anh recruit_dot_left tu 21/11) KHONG phai do anh mau (btn_free khop 1.0) ma do bot chuyen sang tab cao cap truoc; nay nhan het tab hien tai roi moi vao tab co cham do.
- Reddots: cham do intel/play/rally/campaign ma buoc rieng con cho trong luot -> de buoc rieng (live3 tinh bao an 4/4 phut ngan sach). Them quet nhan qua cuoi luot (thu bao cao moi sinh sau tran).
- Gia han khien ngay thuong: Hiep uoc chi khi khien con >= 60 phut (chuan bi 1h khong bao ho) - lech yeu cau P10-7, cho chu du an quyet.

## Tried and ruled out
- Tin "chieu mo khong thay nut" la loi anh mau: chay _recruit_once tren chinh anh luu thi bam dung - anh luu chup SAU khi bot da roi tab.

## Watch out
- O "Cap" tim kiem: DEL gui lien tiep bi mat (10 -> 1), game nhan so qua nut "OK" thanh nhap lieu ban phim ao (nen trang y 870-950, OK 511,910), khong qua Enter. Chua kiem duoc 'input text' co vao khong.
- Mo khoang san: bang "Chuc mung nhan duoc" sau ruong che tieu de -> moi buoc sau phai dong bang truoc khi find('play/mine_title').
- Qua dac biet: hieu ung nhan cham > 1.2 s -> so sanh man ngay se bo nham nut.

In the code: bot/modules/play.py world_popup_kind/pre_check, bot/claimloop.py current_then_tabs, bot/modules/gather.py type_level/keyboard_bar, bot/modules/reddots.py defer_to_step/final_claims, bot/modules/shield.py plan/peace_ok_for_renew; docs/strategy/p10-report.md
