---
title: "Phien quan leo cap bang Tim kiem roi bam sprite duoi mui ten, khong bam giua man; nut Nhay lay dong tren cung chu khong lay nut khop nhat"
author: Trần
date: 2026-11-27
branch: p13m
cost: { minutes: 30, tokens: 445810 }
id: l-5bc5209e
scope: repo
status: active
src: agent
touches:
  - tests/legacy/test_p13m_nhay_expand_rebel.py
  - docs/strategy/p13m-report.md
  - bot/build.py
  - bot/modules/mainquest.py
  - bot/modules/arrow.py
  - bot/world_target.py
  - bot/modules/rebels.py
  - bot/modules/expand.py
  - bot/resources.py
  - bot/guide_tile.py
---

## Decided
- Chu du an (t106u, t107u, 27/11/2026): nha chinh thieu dieu kien thi chi bam "Nhay" cua dong dau chua dat; phien quan mo khoa tuan tu nen bang "Toi da co the tan cong cap N" -> "Tim kiem" -> bam sprite duoi mui ten, lap toi khi co "Tan cong"; phien quan tren o do trong thanh thi bam than con quai. Moi tran phai qua cong "Thang toan dien".
- Nguyen nhan "Nhay" co the sai dong: lay nut khop mau cao nhat, ma ba nut khop 0,997-0,999. Lay nut tren cung.
- Dong tai nguyen khong bam "Nhan cang nhieu": giu luong "Tang cap" -> popup thieu tai nguyen -> chi "Dung dao cu" (khong doan man ma nut do mo ra).
- Luat moi cho dich tren o do trong thanh phai nam TRONG luat o do cu cua tan thu (cung gioi han 6 lan bam mot o); ly do bat dau bang chuoi cu de hoi quy van khop. Diem bam cao hon tam o 0,15 be ngang o: trung than o ca quai, xe tang, jeep.

## Tried and ruled out
- Bam diem co dinh giua man sau "Tim kiem" (P12-4): chu du an bao sai. Khong co mui ten thi chi nhan sprite co nhan "Phien quan".
- Chi khop nut "Tan cong" dung ti le: anh chu du an co nut lon hon mau 6 % (khop 0,61, o ti le 0,94 khop 0,97) nen phai thu them ti le.
- Test cu khang dinh cham giua man bi bo qua trong worktree vi thieu anh: phai chay lai tren ban sao co anh cua may chinh moi thay.
- Luat rieng chen truoc luat o do: ghi de 3 khung tan thu da kiem (xe dau lau, cot sang bi che) va bo mat gioi han lan bam.
- Diem bam cao 0,25 be ngang o: sat mep tren xe jeep.

## Watch out
- Chua chay live. Khong co khung hinh man hien ra sau khi bam con quai trong thanh.
- Cong du doan thang nay ap ca man quan doan cu va ca luc tan thu; chu xanh khong doc duoc thi bo tran.
- Anh chu du an la ban cat: test bang phien quan phai dat vao khung 540x960 o (1,138) cho trung vung nut / tieu de.
- npc_max_ratio 0,3 van co the chan phien quan cap thap tren may luc chien yeu.

In the code: build.first_jump; guide_tile.find_rebel (BODY_UP); expand.fight_rebel / try_city_rebel; mainquest.npc_popup, find_attack (NPC_SCALES), npc_search, tap_rebel; world_target.rebel_near, pick(reach_x); tests/legacy/test_p13m_nhay_expand_rebel.py; docs/strategy/p13m-report.md.
- Trong worktree moi, hoi quy anh tan thu va nhieu test npc bi BO QUA vi thieu anh (chi o thu muc chinh) nen bo test xanh van sot hong. Chay lai tren ban sao tam co them tests/fixtures va anh data/pm-shots tu thu muc chinh.

In the code: guide_tile.BODY_UP, expand.REBEL_WHY, tutorial.decide buoc 5d, tools/check_tutorial.py, tests/regression/test_perception.py.
