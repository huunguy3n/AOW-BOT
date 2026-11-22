---
title: Status of the LDPlayer multi-account manager project
author: Trần
date: 2026-11-21
id: l-d29fdcf6
scope: repo
status: active
touches:
  - backups/MFarm07-pre-poc.ldbk
  - backups/MFarm08-pre-poc.ldbk
  - docs/account-manager/Account-Inventory.md
  - poc/ident.sh
---

## Decided
Project: one LDPlayer instance, many AoW accounts, by swapping app data. As of 2026-11-17: Phase 0 + Phase 1 PoC done (reports in docs/account-manager/). Option A (multi-user) blocked: game exits via Google Play LicenseClient in secondary users, max 4 users. Option C passed 10/10 switches after hardening (pm disable-user during write, uid-based process check, SHA-256 verify, auto-rollback). Test instance #7 = emulator-5568, root mode on, .ldbk at backups/MFarm07-pre-poc.ldbk. User wants approval before each phase.

**Why:** user's working rule — no next phase without explicit confirmation.

Cross-instance test #7→#8 passed (2026-11-17): guest slot works on an instance with different model/serial/MAC/IMEI; ANDROID_ID was the same (#8 is a disk clone of #7 — both hold the SAME game account), so different-ANDROID_ID is still unproven. #8 = emulator-5570, root on, .ldbk at backups/MFarm08-pre-poc.ldbk.

Inventory 2026-11-17 (docs/account-manager/Account-Inventory.md): two game builds — `.vn` 2.5.16 on #0,#1,#7,#8 and Global `com.ageofwarpath.globalwarzone` 3.6.0 on #2–#6. Only 4 distinct stored identities (VN-1=#0, VN-2=#1/#7/#8, GL-1=#2/#6, GL-2=#3/#4/#5); all 9 share one ANDROID_ID. Unresolved: whether user switches accounts in-game (JOY login) — asked the user.
…

## Watch out
before consolidating, inventory account identity (JOY_ACCOUNT_ID hash via poc/ident.sh) on all 9 instances — some may be clones. Related: aow-local-guest-accounts

_From Claude Code's memory of this repo, last updated Nov 18._
