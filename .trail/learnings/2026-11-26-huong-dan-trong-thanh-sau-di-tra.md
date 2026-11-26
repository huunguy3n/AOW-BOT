---
title: "Huong dan trong thanh sau Di cua Tinh bao: bam vat trong o sang xanh la, khong dung toa do ban do the gioi; het quan doan thi dung Tinh bao ca luot ghe"
author: Trần
date: 2026-11-26
branch: p13j
cost: { minutes: 25, tokens: 404029 }
id: l-124dc4bb
scope: repo
status: active
src: agent
touches:
  - bot/guide_tile.py
  - bot/tapguard.py
  - tests/legacy/test_p13j_intel_guide.py
  - docs/strategy/p13j-report.md
  - bot/modules/notify.py
  - bot/intel_rules.py
  - bot/modules/intel.py
---

## Decided
- Chu du an (26/11/2026): sau "Di", muc tieu co the nam TRONG THANH. Bam vat trong o sang xanh la (cot sang xanh / ban tay trang), khong bam linh (o xanh lam) va khong bam bong bong tron giua tay va vat.
- Dang o thanh pho ma khong thay huong dan thi khong bam gi: toa do du phong cua ban do the gioi roi dung vao linh (nguyen nhan "bam hut").
- Tam o on dinh hon dau ngon tay (tay nhap nho), nen co tay thi van uu tien tam o duoi tay.
- Het quan doan ranh -> dung Tinh bao het luot ghe, chan ngay trong ham tinh bao dung chung vi co 3 duong goi (buoc rieng, cham do, notify). Truoc do co o danh sach STOP chi thoat 1 vong, luot ghe #1 gap no_march 4 lan.
- Khong dung som khi hanh quan vua day: hop tiep te khong ton quan doan.

## Tried and ruled out
- Mau ban tay cu chi khop 0.62 voi ban tay moi -> cat mau moi.
- Nhan o bang thanh phan lien thong cua mat na xanh: o bi vat che nen vo vun, bong bong ben canh dinh vao -> khop vien hinh thoi nhieu ti le, tinh theo nua yeu hon.
- Chi dua vao cot sang: cong buff trong tran chay duong va vien o che do xay cung dat -> them dieu kien dang o thanh pho, loai che do xay bang nut X.

## Watch out
- Chua chay live. O DO trong thanh (linh o lam, dich o do) va popup "Phien quan" khong khop nut Tan cong van chua xu ly.
- test_p13b_cham_do_khong_doi fail trong worktree moi vi thieu anh trong data/ (khong co trong git), khong phai do thay doi code.

In the code: bot/guide_tile.py (TILE_TH, BEAM_MIN 50, follow_city, tap_and_check); notify.intel / intel_stopped, ctx.intel_stop; templates/intel/point_hand.png; docs/strategy/p13j-report.md.
