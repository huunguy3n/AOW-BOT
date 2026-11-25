---
title: "Cham do tim nut that bang contour, khong offset mu, va moi lan cham deu kep vao man 540x960"
author: Trần
date: 2026-11-25
branch: p7-live-fixes
cost: { minutes: 9, tokens: 73951 }
id: l-806c7056
scope: repo
status: active
src: agent
touches:
  - bot/ctx.py
  - bot/device.py
  - bot/modules/notify.py
  - tests/legacy/test_p13b_cham_do_khong_doi.py
---

## Decided
Chấm đỏ: bấm tâm vật sở hữu tìm bằng contour (mép phải ~x chấm, mép trên ~y chấm), không tìm thấy thì bỏ chấm vào danh sách đen, không đoán offset. Mọi lần chạm/vuốt kẹp vào 0..539 x 0..959 và ghi WARNING.
## Tried and ruled out
Đổ lỗi cho tốc độ settle/skip_recheck (P13-2): không giải thích được y=964, giữ nguyên.
## Watch out
Live6b #5: offset (x-48,y+70) rơi khoảng trống dưới nút thấp và ra ngoài màn (y=964).
In the code: bot/modules/notify.py owner_box/dot_tap_points, bot/device.py clamp_xy, bot/ctx.py tap; commit 7838e6e.
