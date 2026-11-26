---
title: "Truoc khi bat may phai kiem file cau hinh LDPlayer, chi sua khi may da tat han; nguyen nhan #0 ve mac dinh chua xac dinh"
author: Trần
date: 2026-11-26
branch: p13h
cost: { minutes: 10, tokens: 221828 }
id: l-36443c2f
scope: repo
status: active
src: agent
touches:
  - bot/ldconfig.py
  - bot/device.py
  - bot/runner.py
  - main.py
  - config.yaml
  - tools/snap.py
  - tests/legacy/test_p13h_ldconfig.py
  - bot/hang.py
  - tests/legacy/test_p9_hang_human.py
  - tests/legacy/test_p6_rollout.py
---

## Decided
Chu du an (t93u-t95u, 26/11/2026): may #0 bi LDPlayer tra ve mac dinh (man ngang 1280x720, ADB tat). Truoc khi bat may, bot doc file cau hinh may; sai do phan giai / DPI / ADB thi sua, chi khi may DA TAT HAN. Chi duoc doi 3 gia tri do; cac khoa dinh danh (IMEI, model, android id, IMSI, MAC, hang, sim, so dien thoai) khong bao gio dung vao. May dang chay thi chi canh bao, sua o lan bat sau (khong tu tat may cua chu).

ldconsole modify khong co co bat ADB (help v9.5.15.1), nen rieng ADB phai ghi thang vao file: thay tai cho trong van ban goc (khong dump lai JSON) roi kiem JSON chi khac dung 1 khoa.

In the code: bot/ldconfig.py, LDConsole.check_display / state / quit trong bot/device.py, config.yaml ldplayer.fix_display / resolution / dpi / config_settle_s.

## Tried and ruled out
- "Bot tat manh may luc LDPlayer dang ghi file": log 26/11 khong chung minh. Ma khong co taskkill / quitall / reboot; lan ghe #0 cuoi con tot ket thuc binh thuong 01:53:14, lan sau 02:24 ADB da hong. Dung ghi no la nguyen nhan da xac nhan.
- Coi "cot Android cua list2 = 0" la da tat: quit tra ve gan nhu tuc thi, tien trinh may co the con dang ghi. Nay cho ca PID thoat.

## Watch out
- Cot 6, 7 cua list2 la PID (-1 khi tat) theo dinh dang LDPlayer cong bo, CHUA doi chieu tren may that. Neu sai: log "tien trinh may chua thoat" moi lan tat va cau hinh sai khong duoc sua.
- Chua chay that lan nao (cam goi ldconsole / adb trong phien nay).
