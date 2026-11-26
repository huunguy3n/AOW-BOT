---
title: Popup mo khoa binh chung phai nhan rieng bang chu tieu de va chi bam Xac nhan; mau nut Di cua Tinh bao khop ca nut Den tren popup
author: Trần
date: 2026-11-26
branch: p13k
cost: { minutes: 10, tokens: 236210 }
id: l-436ef762
scope: repo
status: active
src: agent
touches:
  - bot/unlock_popup.py
  - logs/p13k_wire.py
  - logs/p13k_probe.py
  - tests/legacy/test_p13k_unlock_popup.py
  - CLAUDE.md
  - docs/strategy/p13k-report.md
  - bot/ctx.py
  - bot/vision.py
  - bot/modules/tutorial.py
---

## Decided
Chu du an (26/11/2026): popup "Mo khoa Binh chung nay" -> chi bam "Xac nhan" (mien phi), khong bao gio "Den".
Nhan bang ca hai: mau nut Xac nhan (chi nua phai) va chu tieu de so bang mat na mau vang, vi nen sau tieu de la
thanh pho dang song. Popup de lo thanh nut duoi nen is_home van True: phai hoi popup nay truoc is_home / city.
Chan nut Den ngay trong ham cham cua Ctx, vi module khac dang chay co the khop mau cua no len nut do.

In the code: bot/unlock_popup.py (find / dismiss / GO_ZONE), Ctx.unlock_guard, screens._identify, tutorial.decide.

## Tried and ruled out
Them common/btn_confirm vao POPUP_CLOSERS: cam, hop thoai "Roi tro choi?" cung co nut Xac nhan.
Chi don popup trong close_popups: khong du. Do tren anh chu: intel/btn_go khop nut Den 0,92 va tutorial.decide
cham (246,198) vao tieu de (luat "o do duoi chan").

## Watch out
Chua chay live, chi 1 anh (bac 2). Cac cho goi thang dev.tap khong qua chot chan nut Den.
test_p13b_cham_do_khong_doi fail trong worktree moi vi thieu anh data/owner-feedback (khong co trong git).
