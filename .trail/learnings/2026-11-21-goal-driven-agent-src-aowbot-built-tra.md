---
title: "Goal-driven agent (src/aowbot) built on branch roadmap-impl 2026-11-21, OFF by default"
author: Trần
date: 2026-11-21
id: l-c6a047f5
scope: repo
status: active
touches:
  - docs/strategy/MASTER-IMPLEMENTATION-PLAN.md
  - data/settings.json
---

## Decided
Master plan docs/strategy/MASTER-IMPLEMENTATION-PLAN.md approved 2026-11-21; implemented on branch `roadmap-impl` (not pushed, not merged to main).
Agent code in src/aowbot (domain/application/infrastructure/interfaces/app), enabled per machine only via data/settings.json `instances.<idx>.schedule.mode = "agent"` (global loop must be smart). MVP (march loop on #1) NOT yet enabled/run live.

Owner decisions (2026-11-21): farms prioritize ContinuousConstruction until HQ >= gather.min_hq_level (9), then farming; MVP on #1 only after shadow/dry-run passes; no fixture images in git (CI skips image regressions); English identifiers in src/aowbot, comments Vietnamese without diacritics.

**Why:** owner wants measured, phased progress; live runs need owner to start LDPlayer.

## Watch out
pending items need owner: one live pass for perf/inv data, enabling agent on #1, A-OPT-1 (reddots order), rebels.join templates, keep_alive threshold. See aow-test-one-pass-recheck, aow-main-account-i1.

_From Claude Code's memory of this repo, last updated Nov 21._
