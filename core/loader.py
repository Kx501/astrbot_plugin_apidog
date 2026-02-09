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


DEFAULT_RETRY_STATUSES: frozenset[int] = frozenset({500, 502, 503, 429})


def load_config(data_dir: Path) -> dict[str, Any]:
    """Load config.json for global defaults (timeout, retry, retry_statuses). Missing file or keys use built-in defaults."""
    path = data_dir / "config.json"
    raw = load_json(path, {})
    if not isinstance(raw, dict):
        raw = {}
    timeout = raw.get("timeout_seconds")
    if isinstance(timeout, (int, float)) and timeout > 0:
        timeout_seconds = float(timeout)
    else:
        timeout_seconds = 30.0
    retry_raw = raw.get("retry")
    retry: dict[str, Any] | None = None
    if isinstance(retry_raw, dict):
        max_a = retry_raw.get("max_attempts")
        backoff = retry_raw.get("backoff_seconds", 1)
        if isinstance(max_a, (int, float)) and max_a > 0:
            retry = {
                "max_attempts": int(max_a),
                "backoff_seconds": float(backoff) if isinstance(backoff, (int, float)) else 1.0,
            }
    raw_statuses = raw.get("retry_statuses")
    if isinstance(raw_statuses, list):
        retry_statuses = frozenset(
            int(x) for x in raw_statuses
            if isinstance(x, (int, float)) and 100 <= int(x) <= 599
        )
        if not retry_statuses:
            retry_statuses = DEFAULT_RETRY_STATUSES
    else:
        retry_statuses = DEFAULT_RETRY_STATUSES
    return {"timeout_seconds": timeout_seconds, "retry": retry, "retry_statuses": retry_statuses}


def merge_client_options(global_config: dict[str, Any], api: dict) -> dict[str, Any]:
    """Merge global config with per-API overrides. Returns effective timeout_seconds and retry."""
    timeout = api.get("timeout_seconds")
    if isinstance(timeout, (int, float)) and timeout > 0:
        timeout_seconds = float(timeout)
    else:
        timeout_seconds = global_config.get("timeout_seconds", 30.0)
    retry_override = api.get("retry")
    if retry_override is False or retry_override == 0:
        retry = None
    elif isinstance(retry_override, dict):
        max_a = retry_override.get("max_attempts")
        backoff = retry_override.get("backoff_seconds", 1)
        if isinstance(max_a, (int, float)) and max_a > 0:
            retry = {
                "max_attempts": int(max_a),
                "backoff_seconds": float(backoff) if isinstance(backoff, (int, float)) else 1.0,
            }
        else:
            retry = None
    else:
        retry = global_config.get("retry")
    retry_statuses = global_config.get("retry_statuses", DEFAULT_RETRY_STATUSES)
    return {"timeout_seconds": timeout_seconds, "retry": retry, "retry_statuses": retry_statuses}


def load_schedules(data_dir: Path) -> list[dict]:
    """Load schedules.json. Returns schedules array; missing file or non-list -> []."""
    path = data_dir / "schedules.json"
    raw = load_json(path, {})
    if isinstance(raw, dict):
        schedules = raw.get("schedules")
        if isinstance(schedules, list):
            return schedules
    return []


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
