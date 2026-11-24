---
title: "P12: Hiep uoc dang chuan bi khong phai khien, o Cap Co giap chi nhan boi so 5, cham do ton thoi gian vi thao tac lap ben trong"
author: Trần
date: 2026-11-24
branch: p7-live-fixes
cost: { minutes: 54, tokens: 321659 }
id: l-03e7aad6
scope: repo
status: active
src: agent
touches:
  - bot/ctx.py
  - bot/runner.py
  - tests/legacy/test_p12_popup_retry.py
  - tests/legacy/test_p9_hang_human.py
  - bot/modules/construct.py
  - config.yaml
  - src/aowbot/perception/eval/names.py
  - templates/build/road_cancel.png
  - templates/build/road_confirm.png
  - templates/build/road_icon.png
---

## Decided
- Khien ngay thuong (live4): Hiep uoc hoa binh dang "chuan bi" 1h KHONG bao ho -> dung Hiep uoc xong doc lai khien, chua 'on' thi dung vat pham ngay; Hiep uoc dang chuan bi trong tri nho -> bo dong 8h, dung vat pham.
- O "Cap" tim Phan quan Co giap: moi lan +/- doi 5 cap (anh #1 s184116/s184141: 5 <-> 10) -> cap 7/8/9 khong ton tai; dich ve boi so (snap_level) thay vi go cap le.
- Nhiem vu "Kich sat phien quan Lv.N" tren nha chinh < 6 van danh le theo thanh nhiem vu (truoc: npc_skip vi world.min_hq_level 6). Luat HQ < 15 chi cam tap ket Co giap.

## Tried and ruled out
- Tin reddots cham 240 s vi vong ngoai lap cung cham do: vong ngoai da loai cham sau 1 lan vo ich; thoi gian mat o thao tac LAP BEN TRONG (VIP @414,175 nhan 0 o reddots + rewards, o phuc loi @139,530 bam 4-5 lan, 20-40 s/lan) -> danh sach den theo lan ghe (TapGuard) o tung cho cham.
- Tin #5 ket popup goi tra phi: khung that la popup "Chien dich 1" co mui ten V huong dan o "Tan cong" - game chan X va Back.

## Watch out
- Bang "Tang cap VIP": nut "Dung" (nen xanh dam) chi o hang vat pham DA CO; hang "Mua va dung" nut xanh ngoc co kim cuong - loc ca bang anh mau (th 0.92) lan OCR nhan "Mua"/chu so.
- Hop xay duong: nut xanh khac khop road_confirm 0.88 (s192252) -> bat buoc th 0.93 + nut Huy ben trai cung hang.

In the code: bot/modules/shield.py plan/options, bot/modules/defense.py peace_label_status, bot/tapguard.py, bot/modules/rewards.py vip_point_buttons/vip_points, bot/modules/gather.py snap_level/set_level, bot/modules/mainquest.py npc_popup_action/npc_search, bot/modules/construct.py roads, bot/ctx.py popup_escape, bot/runner.py retry_after_recover; docs/strategy/p12-report.md
