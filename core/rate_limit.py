# -*- coding: utf-8 -*-
"""Per (user_id, api_key) rate limit. In-memory only, single process."""

from __future__ import annotations

import time
from typing import Any

_RECORDS: dict[tuple[str, str], list[float]] = {}
_LOCK: Any = None


def _get_lock() -> Any:
    import threading
    global _LOCK
    if _LOCK is None:
        _LOCK = threading.Lock()
    return _LOCK


def _parse_rate_limit(api: dict) -> tuple[int, int] | None:
    """Return (max_count, window_seconds) or None. Only supports object {\"max\": N, \"window_seconds\": S}."""
    rl = api.get("rate_limit")
    if isinstance(rl, dict):
        max_c = rl.get("max")
        win = rl.get("window_seconds")
        if max_c is not None and win is not None:
            try:
                return int(max_c), int(win)
            except (TypeError, ValueError):
                pass
    return None


def check_and_record(
    api: dict,
    user_id: str | None,
    api_key: str,
) -> tuple[bool, str]:
    """
    If api has rate_limit, check (user_id, api_key) against sliding window;
    if under limit, record this call and return (True, ""); else return (False, msg).
    """
    parsed = _parse_rate_limit(api)
    if not parsed:
        return True, ""
    max_count, window_seconds = parsed
    uid = user_id if user_id else ""
    key = (uid, api_key)
    now = time.monotonic()
    lock = _get_lock()
    with lock:
        rec = _RECORDS.get(key, [])
        cutoff = now - window_seconds
        rec = [t for t in rec if t > cutoff]
        if len(rec) >= max_count:
            return False, "调用过于频繁，请稍后再试。"
        rec.append(now)
        _RECORDS[key] = rec
    return True, ""
