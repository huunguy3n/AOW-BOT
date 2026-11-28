---
title: "Hoc may chan cho chet o moi lan cham cua module, van cham thu lai thua dan"
author: Trần
date: 2026-11-27
branch: p7-live-fixes
cost: { minutes: 63, tokens: 759967 }
id: l-d19ed804
scope: repo
status: active
replaces: l-327aca33
src: agent
touches:
  - tests/legacy/test_ml_skip_dead.py
  - tools/learn.py
  - bot/learn.py
  - bot/ctx.py
  - config.yaml
  - docs/strategy/ml-roadmap.md
  - docs/strategy/MASTER-IMPLEMENTATION-PLAN.md
  - tools/report_ro.py
  - tests/legacy/test_ml_m1.py
  - bot/imitate.py
---

## Decided
Chu du an (27/11/2026, "Lam di"): truoc day Learner biet cho chet nhung chi goto dung -> module van cham (gather/btn_recommended an 1/514, notify.* hang tram lan). Nay moi lan cham qua Ctx hoi Learner.skip_tap. Chet = ti le an < dead_rate VA truot LIEN TIEP >= dead_min (1 lan an la song lai, khong doi thong ke tich luy ma goto/web dang dung). Van cho cham thu lai sau probe_min phut, gap doi, toi da probe_cap_h -> nut/man doi thi tu phuc hoi.
Chu du an duyet M0+M1 (27/11/2026). Doan cham vo ich: dac trung = dHash 8x8 cua vung 96x96 quanh diem cham (chinh la ten file crop da luu trong bang exp, khong can doc anh), hang xom lech <= 4 bit, cung o luoi +-1, >= 5 hang xom, >= 90 % truot. Du phong: diem khop +-0,005. Do offline 14 ngay (bo-ra 30 % moi nhat): bo 608/1631 lan truot, dung 98,2 %. Vi du tab lien minh khop 0,994 ma truot = tab da mo san (nguong cao hon khong giup, phai nhin trang thai).
Chan = KHONG gui cham nhung tra ve nhu da cham (tap_tpl True, tap_first ten mau): ket qua du doan giong het nen module khong doi hanh vi, chi do ton thoi gian. Moi anh mau / ham tu kiem bo-ra, chi chan khi dung >= 95 % tren >= 5 lan doan; 5 % van cham that de tiep tuc hoc.
Chu du an noi "tich hop M2" (28/11/2026) khi M1 chua nghiem thu. Moi phan M2 o che do bong: ghi tran vao battle_ev, xac suat thang chi ghi kem (p_win), gia tri buoc va thu tu de xuat chi hien tren web/report, nha chinh dung yen chi bao cao. Runner va quyet dinh danh/bo khong doi, de so do M1 khong bi lan.
Ghi tran bang cach boc ham san co (campaign.battle, play.fight / power_check / _loot_result / run, notify.legion_march) trong battles.install() goi tu Runner, vi play.py / notify.py dang co thay doi chua commit cua phien khac; boc thi khong dung vao file do. Cuop xe lay luc chien ho ve + ta qua thread-local giua power_check va _loot_result.
Ly do nha chinh dung yen nam o fact hq_plan.status (wait_builder / wait_resources / unreached), khong o runs.note (luon trong).

## Tried and ruled out
Reset thong ke [ok, n] ve [1,1] khi cham an: bo, vi doi nghia "cho chet" cua goto va bang web; dung bo dem truot lien tiep rieng (streak).
Tra False khi chan (ban J1 dau): module tuong khong thay nut, co the bo do viec; doi sang "coi nhu da cham".
Nang nguong khop rieng tung anh mau: khong cuu duoc truong hop khop cao ma truot.

## Watch out
Chua chay live. Tren du lieu that 27/11 se chan ~40 o (phan lon notify.claim_content / event_tiles / heroes / hub, ca tutorial/btn_auto_formation an 9 %). Cham bi chan tra ve nhu khong thay nut (tap_tpl False, tap_first None) -> module co the doi thu; neu buoc nao ket vi vay, them vao learn.skip_exempt. Mot so cho chet la loi module, chan chi giam cham vo ich.

In the code:
- bot/learn.py: Learner.skip_tap, streak/probe, summary()['ml_skips']
- bot/ctx.py: Ctx.ml_skip goi trong tap / tap_tpl / tap_first; exp kind='ml_skip' (khong tinh vao thong ke)
- config.yaml learn.skip_dead / probe_min / probe_cap_h / skip_exempt
- tests/legacy/test_ml_skip_dead.py; xem: python tools/learn.py report, web tab Hoc & Agent
Anh chi dung de tinh dHash khi chup trong 5 s (ctx._img_t); test phai dat _img_t = time.time(), neu khong se roi ve luat diem khop. Thu muc crop day 20000 file nhung ten hash van duoc ghi nen dac trung khong mat. Chua chay live.

- bot/learn.py: Learner.noop_gate / predict_noop / noop_valid / _noop_vote, scoreboard, noop_status
- bot/ctx.py: Ctx.ml_skip (tap / tap_tpl / tap_first), Ctx._imitate_unknown (M1-3)
- config.yaml learn.skip_noop, noop_*, imitate_unknown
- python tools/report_ro.py --ml 7 ; tests/legacy/test_ml_m1.py
Ham nao goi bang ten import truc tiep (from ... import battle) se khong duoc boc. Gia tri buoc "viec / phut" danh gia thap buoc xay dung - can trong so theo muc tieu nha chinh truoc khi dung de doi thu tu. Bang battle_ev chi co du lieu sau khi khoi dong lai bot.

- bot/battles.py, bot/mlinsight.py; src/aowbot/domain/battle_model.py, stepvalue.py, hqstall.py
- memory.py bang battle_ev + log_battle; config ml.battle_log
- python tools/report_ro.py --ml ; web tab Hoc & Agent
