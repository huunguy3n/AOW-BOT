---
title: "P7 live #1: quests khong chay vi may #1 tat buoc, chien dich thua vi khong xac nhan duoc vao tran nen khong lai; Hiep uoc giua ngay chien tranh van chua dung"
author: Trần
date: 2026-11-23
branch: p7-live-fixes
cost: { minutes: 39, tokens: 389783 }
id: l-5ed89847
scope: repo
status: active
src: agent
touches:
  - CLAUDE.md
  - bot/modules/defense.py
  - tests/legacy/test_p7_shield.py
  - bot/modules/warday.py
  - bot/scheduler.py
  - bot/stepgate.py
  - config.yaml
  - src/aowbot/domain/warday.py
  - tests/legacy/test_p7_timed_login.py
  - bot/device.py
---

## Decided
P7 (chu du an 2026-11-24, sau live #1 tren may #1). Buoc quests khong chay lan nao vi data/settings.json may #1 co modules.quests false (runner bo qua im lang) -> khong sua cai dat cua chu du an; tat quests = chi nhan thuong o tab co cham do, khong bam "Den" (quests.claim_when_off). Tran chien dich thua khong phai chi do luc chien: log "Khong xac nhan duoc dang trong tran" sau 10 s -> steer khong dat ngon tay, khong ne, khong an buff. Campaign dung steer.campaign_battle (battle_hud 0,85 + battle_hud_* + dau hieu tran tan thu) va cho 25 s; that bai luu khung logs/inv/steer_no_battle de cat HUD. Kim cuong mua khien ngay chien tranh (shield_war) khong tinh vao tran 2000/ngay thuong.

## Tried and ruled out
Dung Hiep uoc hoa binh de gia han GIUA ngay chien tranh (chu du an P7-12 noi "moi loai khien ke ca Hiep uoc"): van giu quyet dinh P6 chi dung truoc gio G, vi Hiep uoc can 1h chuan bi va chua biet game co thay khien dang chay khong -> de chu du an quyet (bao cao p7-report).

## Watch out
Nut lam moi dau truong / mo khoang san: neu chu tren nut co so (gia kim cuong / so luot) bot KHONG bam; bam ma hien hop thoai la -> dong, dung. Sau khi cat anh play/btn_arena_refresh can xem nut that co so khong. Su menh: moi cham qua vung cho phep theo man (mission.ALLOW) - neu giao dien lech, bot khong cham thay vi cham nham The thong hanh.

In the code: bot/quest_rules.py quests_mode, bot/runner.py (quests_claim_only), bot/steer.py campaign_battle/ENTER_WAIT_S/GateTrack/flip_ok, bot/modules/defense.py counts_toward_cap, bot/modules/mission.py, bot/modules/play.py arena_refresh/refresh_trucks/is_burning, src/aowbot/domain/warday.py timed_login_*.
