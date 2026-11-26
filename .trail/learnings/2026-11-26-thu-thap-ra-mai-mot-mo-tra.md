---
title: Thu thap ra mai mot mo la do buoc nhay cap cua Co giap dinh sang tab mo; moi loai do lai tu cap 8
author: Trần
date: 2026-11-26
branch: p13g
cost: { minutes: 69, tokens: 1606005 }
id: l-6b96ae37
scope: repo
status: active
src: agent
touches:
  - bot/modules/gather.py
  - tests/legacy/test_p13g_gather_same_mine.py
  - bot/__init__.py
  - main.py
  - run.bat
  - tests/legacy/test_p13g_import_path.py
  - tests/legacy/test_p13g_stuck_screen.py
  - src/aowbot/perception/eval/names.py
  - docs/strategy/p13g-report.md
  - bot/gather_rules.py
---

## Decided
- Chu du an t92u (26/11/2026): moi loai mo tim 8 -> 7 -> 6 ...; trung mo vua chiem thi ha cap hoac sang loai uu tien ke; khong bao gio gui 2 quan doan toi 1 mo. Quyet dinh nay thay phan "nho cap cao nhat con thoa (gather_top) roi bat dau tu do" cua 21/11.
- Goc loi: buoc "o Cap nhay 5 don vi" hoc o buoc phan quan Co giap luu tren ctx va song suot luot ghe, nen thu thap doi cap 3/2/1 thanh 5, Tim ra dung mot mo cap 5 va con tinh dung tich theo cap muon tim (gui doi qua nho). Buoc nhay chi duoc ap cho tab Co giap.
- Nhan dien "cung mo" bang toa do X/Y doc tren ban do, khong chi bang loai/cap + thoi gian di.
- In the code: bot/modules/gather.py step_of, read_mine_xy, own_tile (fact own_tiles); bot/gather_rules.py same_mine, bigger_mine; gather.own_tile_block_min 480, same_mine_type_limit 2; tests/legacy/test_p13g_gather_same_mine.py.
- #0 ngay 26/11/2026 chay 720x1280 (cau hinh LDPlayer doi) -> moi man thanh "unknown", Back tren thanh pho mo "Roi tro choi?", cham Huy truot vi toa do 540x960. Truoc khi cat anh mau hay sua dieu huong, kiem kich thuoc anh trong logs/unknown.
- Thiet bi thu nho khung cung ti le ve 540x960 va nhan lai toa do cham; van can chu du an dat lai may 540x960 DPI 240.
- 2 buoc khong ve duoc thanh pho: dong popup, roi khoi dong lai game, moi bo luot (nav.rescue_max).
- In the code: bot/device.py normalize_frame, Device.scale; bot/runner.py _rescue_city, lost_plan; templates/common/splash_logo.png (man nap game -> cho, khong Back).
- 26/11/2026 09:19 loi "builders has no attribute FillState" khong phai thieu class: cua so start thua huong PYTHONPATH tro toi worktree cu. src cua chinh repo dat dau sys.path, run.bat xoa PYTHONPATH.
- In the code: bot/__init__.py, run.bat, main.py check_import_paths, tests/legacy/test_p13g_import_path.py.

## Tried and ruled out
- Nghi game tra lai mo cu du chon cap khac: sai, log co dong "O Cap: buoc 5 -> dung cap 5 thay cho 3" va anh cham luu cho thay huy hieu cap 5.
- Tang so mo trong state dispatches de nho o da gui: bo, observe ghep dispatches voi doi dang di theo thu tu nen danh sach dai lam sai timeline web; luu rieng trong tri nho.
- Coi la popup/man la moi can them anh mau: 70/71 anh nhan ra ngay sau khi thu nho.

## Watch out
- Trang thai gan len ctx song qua nhieu buoc trong cung luot ghe: thuoc tinh rieng cua mot tab/man phai gan theo tab.
- Khong doc duoc o "Cap" thi khong duoc dung bang dung tich theo cap.
- Chua chay gather that sau ban sua.
- Cam ung sendevent o do phan giai khac chua do tren may that (gia dinh truc tho ti le theo do phan giai).
- Goi aowbot con duoc cai editable tro vao cay chinh, nen script trong worktree khong import bot truoc se lay ma cay chinh.
- Khi kiem trong worktree khong gan PYTHONPATH ben trong cua so se start bot.
