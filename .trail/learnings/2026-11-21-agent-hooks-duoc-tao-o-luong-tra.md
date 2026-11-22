---
title: "Agent hooks duoc tao o luong chinh nhung runner goi tu luong nen, nen ket noi SQLite phai cho phep khac luong"
author: Trần
date: 2026-11-21
branch: roadmap-impl
cost: { minutes: 144, tokens: 1405827 }
id: l-44b9e3cc
scope: repo
status: active
src: agent
touches:
  - CLAUDE.md
  - docs/strategy/implementation-roadmap.md
  - tests/integration/test_web_agent.py
  - web/agent.html
  - web/index.html
  - web/server.py
  - bot/ctx.py
  - bot/device.py
  - bot/learn.py
  - bot/modules/alliance.py
---

## Decided
- Ket noi doc memory.db cua agent mo voi check_same_thread=False va mot khoa threading: hooks tao 1 lan trong main.py, runner goi due_event/next_at tu luong nen.
- Sau "Den", doi man dung yen (2 khung lien tiep giong nhau, tran 3-4 s) roi moi tim nut Tang cap; chua thay thi doi them 1 nhip va doc lai 1 lan.
- "Den" vo tac dung -> OCR dai thong bao noi giua man (y 270-380), phan loai: lo dat chua mo (12 h), thieu cong trinh dieu kien "X mo khoa cap N" (6 h), khong ro (quests.none_retry_h, 2 h). Nho theo dau van tay dong nhiem vu, bo qua toi han.
- Dau van tay dong = dhash 12x12 vung TIEU DE (tren nut Den), khong lay so tien do x/y.
- Nut Nhan / Nhan toan bo / Den tim theo MAU (xanh ngoc H 84-90 = Nhan, xanh duong H 95-100 = Den) roi OCR chu ben trong; chi bam khi chu khop "nhan" va khong co dau hieu tra phi.

## Watch out
- Loi nay bi nuot thanh WARNING "Agent: khong doc duoc su kien may N" -> agent khong bao gio chay (bang decisions/events = 0).
- Nang hon: scheduler cu bo buoc gather cho may o che do agent -> agent chet = may do KHONG gui quan nao. Khi agent loi, can kiem log + bang decisions truoc khi tin che do agent.
- Bat agent cho ca 7 may trong settings.json (ke hoach chi #1) lam loi lan ra moi farm.

In the code:
- src/aowbot/infrastructure/sqlite/legacy_memory_reader.py: LegacyMemoryReader.__init__/_rows
- test: tests/contract/test_state_source.py::test_agent_hooks_work_from_runner_thread (fail tren code cu)
- runner nuot loi: bot/runner.py _spawn_agent
- Thong bao noi chi hien vai giay: doc tu khung chup NGAY sau khi cham, roi moi den khung hien tai.
- Tin tro giup lien minh ("... giup ban xay dung cap 4 ...") cung nam o dai do: khong duoc phan loai thanh ly do chan.
- Tab Chinh co nhieu dong khong phai xay (huan luyen, kich sat phan quan, tuong, dau truong) -> luon 'none'; chung bi chan theo no_effect, khong phai loi.

- bot/ctx.py Ctx.settle; bot/build.py upgrade_here(late=); bot/game_msg.py; src/aowbot/domain/blockers.py
- bot/modules/quests.py row_key / remember_block / ROW_MAX_DIST=12 (cung dong 0-3 bit, khac dong >=28)
- state.json: instances.<idx>.quest_blocks; anh kiem: tests/fixtures/screen_loop (local)
- Trang thai tai khoan thieu khoa moi (phat lai shadow tu du lieu cu) phai tra "chua biet", khong KeyError.
- Bo doc hang cho khong doc duoc "1/1" (chu so 1 manh) -> research "?" o #1.

- bot/buttons.py claims()/with_text(); Ctx.claim_buttons; AccountState.get mac dinh UNKNOWN

## Tried and ruled out
- Them anh mau / ha nguong: anh mau btn_upgrade_icon khop 0,93-0,97 tren anh chup sau do -> loi la thoi diem doc, khong phai anh mau.
- Khoa dong theo so thu tu: cac dong dich len khi nhan thuong -> chan nham dong.
- Chi dung mau: khao sat 350 anh that thay cung mau xanh ngoc con co Chieu mo, Dong, Bat dau lai va nut MUA bang kim cuong ("@ 1000").
