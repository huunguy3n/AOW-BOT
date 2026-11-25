---
title: "Nhà chính chờ thợ không được giữ thợ rảnh, và cấp nhà chính chỉ ghi khi đọc hợp lý"
author: Trần
date: 2026-11-25
branch: p13d
cost: { minutes: 15, tokens: 284766 }
id: l-8d653e21
scope: repo
status: active
src: agent
touches:
  - bot/steer.py
  - bot/stream.py
  - tests/legacy/test_p13d_steer.py
  - bot/build.py
  - src/aowbot/domain/hqplan.py
  - tests/legacy/test_p13d_build_wait.py
  - tests/unit/test_hqplan.py
  - bot/modules/champion.py
  - bot/modules/reddots.py
  - tests/legacy/test_p13d_champion.py
---

## Decided
Kế hoạch nhà chính ở trạng thái chờ thợ (wait_builder) chỉ nhường thợ cho nhà chính sau giờ thức dậy; trước đó thợ rảnh phải làm việc xây khác. Cấp nhà chính chỉ được ghi khi bằng cấp cũ hoặc +1; nhảy hơn 1 hoặc giảm cần hai lần đọc độc lập có nhãn Xưởng kiến trúc. Chấm đỏ: trí nhớ vô ích hết hạn theo từng lần ghé, và Liên minh/Tình báo/Chiến dịch/Nhận không bao giờ bị bỏ sớm.
## Tried and ruled out
Đổi max_builders mặc định lên 2: bỏ, vì chưa biết máy nào thật sự có thợ thứ hai.
## Watch out
Nhà chính chính là Xưởng kiến trúc trong game này, nên dòng log cố định "Xuong kien truc" không chứng minh được nhãn đọc đúng.
In the code: src/aowbot/domain/hqplan.py (reserve), bot/modules/observe.py (judge_hq), bot/modules/reddots.py (PROTECTED, remember visit).
