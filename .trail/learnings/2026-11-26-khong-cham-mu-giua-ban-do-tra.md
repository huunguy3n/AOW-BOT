---
title: Khong cham mu giua ban do vi trung can cu nguoi choi; menu can cu chi duoc dong; thua Tinh bao thi bo dung lop ghim
author: Trần
date: 2026-11-26
branch: p13l
cost: { minutes: 38, tokens: 573821 }
id: l-4ba25cad
scope: repo
status: active
src: agent
touches:
  - bot/intel_pins.py
  - bot/map_menu.py
  - bot/world_target.py
  - bot/modules/rebels.py
  - bot/modules/mainquest.py
  - bot/modules/gather.py
  - bot/modules/arrow.py
  - bot/modules/tutorial.py
  - bot/ctx.py
  - bot/resources.py
---

## Decided
- Chu du an (26-27/11/2026): KHONG BAO GIO bam menu can cu nguoi choi (Trinh sat / Tap ket / Tin tuc / Tan cong). Nguyen nhan bot cham trung can cu: cac diem "mu" co dinh giua ban do (Tinh bao sau "Di" (268,405)/(268,438)/(265,365), muc tieu giua man cua nhiem vu chinh (272,445), mui ten xanh +95 px). Vi vay co 2 lop: tranh truoc (dau hieu can cu) va hang rao o moi cu cham cua Ctx (thay menu thi chi Back).
- Mui ten xanh: tim vat that (nhan "Phien quan" -> thanh mau -> vat khac nen) roi lam tai cho; menu "Chuyen thanh / Chiem linh" = cham hut.
- Thua Tinh bao: bo dung LOP ghim (bieu tuong + mau), thu lai khi luc chien tang >= 5 %. Ban chan moi tran trong 3 gio bi loai vi lam mat ca cac ghim thang duoc.
- Ghim Phan quan Co giap tu Tinh bao: chi tu nha chinh 15 (rebels.intel_rally_min_hq 0 -> 15), dien giai cau "HQ<15 chi bo rally co giap" - cho chu du an xac nhan.
- Thieu tai nguyen: chi "Dung dao cu" ben trai roi goi nho nhat trong tui.

## Tried and ruled out
- Chi dua vao co / mai khien de tranh can cu: co nuoc khac, the lien minh OCR hay rot dau "(" -> van can hang rao nhan menu.
- Nhan menu bang 1 nut "kiem cheo": "Chiem linh" cung bieu tuong voi "Tan cong" (khop 0,86) -> phai xet theo cap nut.
- Loc "ghim mo" chi theo so diem trang: o den / o khong co ghim bi coi la mo -> them kiem do sang.

## Watch out
- Chua chay song. Mau menu, nhan phien quan, bieu tuong ghim cat tu anh chu du an (cung ti le 540 px).
- Ghim bi ghim khac che vong chan phan loai duoc nhung khong duoc chon de bam.
- Tool/heredoc co the nuot dau "\\" khi va file Python: regex "\b" thanh ky tu backspace. Kiem bang `file <ten>` ("with overstriking").

In the code: bot/map_menu.py, bot/world_target.py (blind_tap_ok, city_near, pick), bot/modules/arrow.py, bot/intel_pins.py, IR.lost_gate, bot/resources.py, Ctx.blocked_tap; test: tests/legacy/test_p13l_*.py; bao cao docs/strategy/p13l-report.md.
