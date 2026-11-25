---
title: "P13: khien ngay thuong chi Hiep uoc 8h mien phi va nha chinh kẹt vi 'Nhay' toi o dat chua xay + tho ranh cuoi luot, khong phai loi buoc"
author: Trần
date: 2026-11-25
branch: p7-live-fixes
cost: { minutes: 83, tokens: 395940 }
id: l-ca9e0bee
scope: repo
status: active
src: agent
touches:
  - docs/strategy/p13-report.md
  - bot/device.py
  - tests/legacy/test_p13_screencap_retry.py
  - bot/ctx.py
  - bot/modules/mission.py
  - bot/modules/reddots.py
  - bot/modules/rewards.py
  - bot/runner.py
  - bot/visit.py
  - config.yaml
---

## Decided
Chu du an (P13, 2026-11-25) ghi de P10/P12: ngay thuong khong dung vat pham khien, khong kim cuong, chi Hiep uoc 8h mien phi; thu 7 chi bat khi thay huy hieu canh dong ho khien. Tieu chi nghiem thu la tien do that (nha chinh len cap), khong phai ti le buoc khong loi.
## Tried and ruled out
Tin ti le buoc 100 % cua live5: nha chinh #3-#6 van cap 4-5. Mẹo ra the gioi roi vao lai thanh pho da co trong goto_hq nhung world_ready=false o HQ<6 nen khong bao gio chay o cac may can nhat.
## Watch out
Nguyen nhan jump_none_d2 (nut Nhay tro toi o dat chua xay) chua sua tan goc, chi rut lui lich none 5 phut. Anh mau P13 cat tu anh dien thoai, chua kiem tren ADB.
In the code: bot/modules/shield.py, bot/modules/upgrade.py (recenter_hq), src/aowbot/domain/hqplan.py, docs/strategy/p13-report.md
