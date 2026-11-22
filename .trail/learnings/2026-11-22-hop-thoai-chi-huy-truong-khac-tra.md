---
title: "Hop thoai Chi huy truong khac dang hanh quan den mo la do doi cua chinh minh, khong phai nguoi choi khac"
author: Trần
date: 2026-11-22
branch: p3-thu-thap
cost: { minutes: 3, tokens: 90725 }
id: l-78be32f9
scope: repo
status: active
src: agent
touches:
  - docs/strategy/implementation-roadmap.md
  - bot/gather_rules.py
  - bot/modules/gather.py
---

## Decided
P3 (PM 2026-11-23): hop thoai sau "Xuat chinh" ("Chu y! Co Chi huy truong khac dang hanh quan den diem tai nguyen nay... [Huy] [Tiep tuc]") hien khi CO DOI NAO (ke ca quan doan khac cua minh) dang di toi mo. Log #1 22/11 16:44-16:48: ca 7 lan la doi minh (cung loai/cap, cung thoi gian di 1008 s, gui 51 s truoc). Mo day gan nhat chi het "day" khi doi toi noi, nen "Tim kiem" cung cap tra lai dung mo do. Cach chan: truoc khi tim bo (loai, cap) co doi minh dang di; truoc Xuat chinh so thoi gian di voi lan gui truoc. Hop thoai van hien -> Huy, KHONG BAO GIO Tiep tuc (co the danh nhau).
## Tried and ruled out
Coi la nguoi choi khac chiem mo va chi Huy roi thu lai: lap vo ich, cung mo bi tra lai moi lan.
## Watch out
gather_unread 111/111 la tru luong None (OCR tren nen cay sang), khong phai tai trong; bang dung tich mo day gather.mine_caps thay OCR hong.
In the code: bot/gather_rules.py own_target, choose_amount; bot/modules/gather.py try_dispatch; config gather.mine_caps, contested_skip_min.
