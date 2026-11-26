---
title: "Bong bong co le nhan bang hinh xoay nhieu goc, va ha cap nha chinh can hai lan doc; cap that cua may 2 va 3 chua chac la 7"
author: Trần
date: 2026-11-26
branch: p13i
cost: { minutes: 55, tokens: 449198 }
id: l-91234986
scope: repo
status: active
src: agent
touches:
  - bot/wrench.py
  - bot/hqlevel.py
  - tests/legacy/test_p13i_wrench.py
  - tests/legacy/test_p13i_hq_gate.py
  - tests/legacy/test_p13d_hq_read.py
  - docs/strategy/p13i-report.md
  - bot/modules/upgrade.py
  - bot/build.py
  - bot/modules/observe.py
---

## Decided
Chu du an (t96u 26/11/2026): tho ranh thi truoc tien bam bong bong tron vang co le tren cong trinh (nang duoc ngay), uu tien nha chinh. Cap nha chinh khong bao gio ha tu mot lan doc; chi ha khi hai lan doc man chi tiet khop nhau, co canh bao.
Nhan bong bong bang hinh bieu tuong o nhieu goc xoay + vong vang + long dia toi + khop anh mau da xoay. Do tren khoang 30 nghin khung da luu: khong thay khop nham.

## Tried and ruled out
Chi khop anh mau hoac chi do trung hinh o mot goc: bo sot nhieu vi bong bong lac nghieng, trong mo va camera thu nho (diem khop xuong 0.45-0.55). Khop nham gan nhat khi noi long la vet dan trong tran.
Dua vao anh mau huy hieu nha chinh de xet uu tien: hiem khi khop tren cac man co bong bong, nen phai dua camera ve nha chinh roi coi giua man la nha chinh.

## Watch out
De bai cho rang may 2 va 3 la cap 7 va bi ghi de thanh 6, nhung log cho thay man nang cap nha chinh bao cap 6 ca truoc lan sau lan doc 7, va bo doc bang avatar tung cho 7 sai. Chu du an chua xac nhan trong game. Dung coi 7 la dung khi sua tiep.
Anh chu gui ghi toa do y khoang 255 la mep tren khung do; tam bong bong that o y khoang 283.
Chua chay that: chua biet bam bong bong mo thang man nang cap hay menu cong trinh; moi bong bong that trong kho anh deu nam tren cung mot cong trinh.
In the code: bot/wrench.py (nguong), bot/hqlevel.py (record, judge_hq), bot/modules/upgrade.py (wrench_upgrades, tap_wrench), docs/strategy/p13i-report.md.
