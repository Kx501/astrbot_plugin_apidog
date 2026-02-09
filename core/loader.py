# -*- coding: utf-8 -*-
"""Load apis.json, auth.json; find api; build config for placeholders."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("apidog.core.loader")


def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return default


def load_apis(data_dir: Path) -> list[dict]:
    path = data_dir / "apis.json"
    raw = load_json(path, {"apis": []})
    apis = raw.get("apis", []) if isinstance(raw, dict) else []
    return apis if isinstance(apis, list) else []


def load_auth(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "auth.json"
    return load_json(path, {})


def load_groups(data_dir: Path) -> dict[str, Any]:
    """Load groups.json. Returns {"user_groups": {...}, "group_groups": {...}}; missing file or keys -> empty dict."""
    path = data_dir / "groups.json"
    raw = load_json(path, {})
    if not isinstance(raw, dict):
        return {"user_groups": {}, "group_groups": {}}
    user_groups = raw.get("user_groups") if isinstance(raw.get("user_groups"), dict) else {}
    group_groups = raw.get("group_groups") if isinstance(raw.get("group_groups"), dict) else {}
    return {"user_groups": user_groups, "group_groups": group_groups}


def enabled_apis(apis: list[dict]) -> list[dict]:
    """Return only APIs with enabled !== false."""
    return [a for a in apis if a.get("enabled", True) is not False]


def find_api(apis: list[dict], api_key: str) -> dict | None:
    for api in apis:
        if api.get("command") == api_key or api.get("id") == api_key:
            return api
    return None


def get_config_for_placeholders(
    auth: dict[str, Any],
    extra_config: dict[str, Any] | None,
) -> dict[str, Any]:
    out: dict[str, Any] = dict(extra_config or ())
    for name, auth_entry in auth.items():
        if isinstance(auth_entry, dict):
            if "value" in auth_entry:
                out[name] = auth_entry.get("value")
            elif "token" in auth_entry:
                out[name] = auth_entry.get("token")
    return out
