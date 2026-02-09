# -*- coding: utf-8 -*-
"""Build request (placeholders), execute httpx, return status/data/text/body/type."""

from __future__ import annotations

from typing import Any

import httpx

from .parse_args import resolve_placeholders
from .auth import apply_auth
from .log_helper import logger

MEDIA_PREFIXES = ("image/", "video/", "audio/")


def _is_media_content_type(ct: str | None) -> bool:
    if not ct:
        return False
    ct = ct.split(";")[0].strip().lower()
    return any(ct.startswith(p) for p in MEDIA_PREFIXES)


async def execute_request(
    api: dict,
    url: str,
    method: str,
    headers: dict[str, Any],
    params: dict[str, Any],
    body: Any,
    auth: dict[str, Any],
    timeout: float | None = None,
) -> tuple[int, Any, str, bytes | None, str | None]:
    """
    Run httpx request. Returns (status_code, data, text, content_bytes, content_type).
    When status is 200 and Content-Type is image/video/audio, content_bytes and content_type are set.
    """
    apply_auth(api, auth, headers, params)
    timeout_val = timeout if timeout is not None and timeout > 0 else 30.0

    try:
        async with httpx.AsyncClient(timeout=timeout_val, follow_redirects=True) as client:
            if method == "GET":
                r = await client.get(url, params=params, headers=headers)
            elif method == "POST":
                r = await client.post(
                    url,
                    params=params,
                    json=body if isinstance(body, (dict, list)) else None,
                    content=body if isinstance(body, str) else None,
                    headers=headers,
                )
            elif method == "PUT":
                r = await client.put(
                    url,
                    params=params,
                    json=body if isinstance(body, (dict, list)) else None,
                    content=body if isinstance(body, str) else None,
                    headers=headers,
                )
            elif method == "PATCH":
                r = await client.patch(
                    url,
                    params=params,
                    json=body if isinstance(body, (dict, list)) else None,
                    content=body if isinstance(body, str) else None,
                    headers=headers,
                )
            elif method == "DELETE":
                r = await client.delete(url, params=params, headers=headers)
            else:
                raise ValueError(f"不支持的请求方法: {method}")

            try:
                data = r.json()
            except Exception:
                data = None

            text = r.text or ""
            content_bytes: bytes | None = None
            content_type: str | None = None
            if r.status_code == 200:
                ct = r.headers.get("content-type") or ""
                if _is_media_content_type(ct):
                    content_bytes = r.content
                    content_type = ct.split(";")[0].strip()

            return (r.status_code, data, text, content_bytes, content_type)

    except httpx.TimeoutException:
        raise
    except Exception:
        logger.exception("ApiDog request error")
        raise
