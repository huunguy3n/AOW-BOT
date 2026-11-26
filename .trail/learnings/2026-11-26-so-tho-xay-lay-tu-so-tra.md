---
title: "So tho xay lay tu so o game bao, khong cung 1 cho farm; cuoi luot lap tho ranh"
author: Trần
date: 2026-11-26
branch: p13e
cost: { minutes: 7, tokens: 175235 }
id: l-c5621b4b
scope: repo
status: active
src: agent
touches:
  - bot/modules/notify.py
  - docs/strategy/p13e-report.md
  - tests/legacy/test_p12_tapguard.py
  - tests/legacy/test_p13e_glow.py
  - bot/build.py
  - bot/hqplan.py
  - bot/modules/observe.py
  - bot/modules/upgrade.py
  - bot/runner.py
  - bot/scheduler.py
---

## Decided
Chu du an (26/11/2026): thợ rảnh phải được dùng hết. Số thợ hiệu lực = y trong "x/y" game báo (tối đa 2), không cứng 1 cho farm; ô chưa có (y=1) thì giữ 1 và bot không bao giờ thuê/mua bằng kim cương. Cuối lượt đọc lại hàng chờ xây, còn thợ rảnh thì chạy lại construct/upgrade/mainquest/quests. Thợ rảnh luôn đưa construct/upgrade/mainquest vào lượt (kể cả lượt Đăng nhập hẹn giờ).
## Tried and ruled out
Đổi mặc định max_builders lên 2: vẫn bỏ (chưa chắc máy nào có ô 2); thay vào đó đọc y từ game (log 26/11: cả 7 máy báo tổng 2).
## Watch out
Cấu hình cứng 1 kẹp mọi nơi (builder_idle, idle_slots, plan_build, quick_wait, hqplan) nên phải sửa đồng bộ. Ô phát sáng bị bấm lặp vì toạ độ nhích 1 px qua mặt tapguard (khóa theo toạ độ chính xác): đã thêm khóa thô 30 px (còn 1 lần bấm/lượt, test p12_tapguard đổi từ 2 xuống 1). Test p13b_cham_do cần data/owner-feedback (gitignore) nên fail trong worktree mới. Editable install trỏ tới E:\AOW-BOT\src: chạy main.py --check trong worktree cần sys.path chèn src.
In the code: src/aowbot/domain/builders.py, bot/build.py max_builders, bot/scheduler.py with_build_steps, bot/runner.py _fill_builders, bot/modules/notify.py glow_dead.
