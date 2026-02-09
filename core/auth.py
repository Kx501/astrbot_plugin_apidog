# -*- coding: utf-8 -*-
"""Apply auth from auth_config to headers/params."""

from __future__ import annotations

import base64
from typing import Any


def apply_auth(
    api: dict,
    auth_config: dict[str, Any],
    headers: dict[str, Any],
    params: dict[str, Any],
) -> None:
    auth_ref = api.get("auth") or api.get("auth_ref")
    if not auth_ref or auth_ref not in auth_config:
        return
    auth = auth_config[auth_ref]
    if not isinstance(auth, dict):
        return
    typ = auth.get("type", "").lower()
    if typ == "bearer":
        token = auth.get("token") or auth.get("value") or ""
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif typ == "api_key":
        key_name = auth.get("header") or auth.get("key") or "X-API-Key"
        value = auth.get("value") or auth.get("token") or ""
        if auth.get("in") == "query":
            params[key_name] = value
        else:
            headers[key_name] = value
    elif typ == "basic":
        user = auth.get("username") or auth.get("user") or ""
        password = auth.get("password") or auth.get("pass") or ""
        if user or password:
            raw = f"{user}:{password}"
            headers["Authorization"] = "Basic " + base64.b64encode(raw.encode()).decode()
    else:
        for k, v in auth.items():
            if k not in ("type", "in") and isinstance(v, str) and v:
                headers[k] = v
