---
title: "Dò mỏ thu thập từ cấp 8 hạ dần, nhớ cấp thỏa, chỉ dò lại khi nhà chính hoặc tướng lên cấp"
author: Trần
date: 2026-11-21
branch: roadmap-impl
cost: { minutes: 4, tokens: 138399 }
id: l-85968ea1
scope: repo
status: active
src: agent
touches:
  - CLAUDE.md
  - docs/strategy/implementation-roadmap.md
  - tests/integration/test_web_agent.py
  - web/index.html
  - web/server.py
  - bot/ctx.py
  - bot/device.py
  - bot/learn.py
  - bot/modules/alliance.py
---

## Decided
Chủ dự án (2026-11-21): gather dò từ cấp 8 xuống, cấp nào tải trọng đội >= trữ lượng mỏ thì đi. Nhớ cấp cao nhất còn thỏa của từng loại mỏ và loại bị khóa theo nhà chính; chỉ xóa trí nhớ khi nhà chính lên cấp hoặc tướng tăng cấp. Mọi giờ trên web hiển thị GMT+7, dạng dd/MM/yyyy HH:mm:ss.
In the code: bot/modules/gather.py (sync_memory, facts gather_sig / gather_top:<loại> / gather_locked:<loại>), bot/modules/notify.py (_hero_levelup tăng fact hero_ups), config.yaml gather.max_level = 8, web/index.html hàm clock.

## Tried and ruled out
Nhớ theo tải trọng đội (march_load): bỏ vì tải trọng đổi theo số lính, chủ dự án muốn chỉ đổi khi nhà chính/tướng lên cấp. Sửa tên nghiên cứu bằng ảnh mẫu: bỏ vì Tesseract chỉ có gói eng, nên dùng bảng từ vựng gần đúng (bot/vnames.py).

## Watch out
Không phân biệt được tướng thuộc quân đoàn thu thập, tướng nào lên cấp cũng làm dò lại. Không đọc được trữ lượng/tải trọng thì không nhớ kết quả (UNREAD). Web cần khởi động lại để tên nghiên cứu cũ được sửa. Bảng VOCAB tự viết, chưa đủ hết tên nghiên cứu.
