"""Cau hinh hieu luc cua 1 may, gop nhu bot cu (config.yaml <- data/settings.json global <- instance)."""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from bot.state import deep_merge


def instance_config(base: Mapping[str, Any], idx: int, settings_path: str) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
    merged: dict[str, Any] = deep_merge(dict(base), settings.get("global"))
    out: dict[str, Any] = deep_merge(merged, (settings.get("instances") or {}).get(str(idx)))
    return out
