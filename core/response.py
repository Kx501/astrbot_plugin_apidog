# -*- coding: utf-8 -*-
"""Parse HTTP response into CallResult (text / media URL / media body)."""

from __future__ import annotations

import json
from typing import Any

from .types import CallResult, ResultType


def _get_nested(obj: Any, path: str) -> Any:
    for part in path.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return None
    return obj


def parse_response(
    api: dict,
    status_code: int,
    data: Any,
    text: str,
    content_bytes: bytes | None = None,
    content_type: str | None = None,
) -> CallResult:
    """
    Build CallResult from request result.
    When response_media_from == "body", use content_bytes/content_type;
    otherwise use data/text to extract URL (existing logic).
    """
    response_type = (api.get("response_type") or "text").lower()
    response_path = (api.get("response_path") or "").strip()
    media_from = (api.get("response_media_from") or "url").lower()

    if status_code >= 400:
        msg = text
        if isinstance(data, dict) and "message" in data:
            msg = data.get("message", msg)
        return CallResult(
            success=False,
            message=f"请求失败 (HTTP {status_code})。{msg}"[:500],
            result_type="text",
        )

    if response_type == "text":
        if response_path and isinstance(data, dict):
            content = _get_nested(data, response_path)
            if content is None:
                content = str(data)
            else:
                content = str(content) if not isinstance(content, str) else content
        elif data is not None:
            content = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            content = text or ""
        msg = content[:5000] if len(content) > 5000 else content
        return CallResult(success=True, message=msg, result_type="text")

    if response_type in ("image", "video", "audio"):
        if media_from == "body":
            if content_bytes and len(content_bytes) > 0:
                return CallResult(
                    success=True,
                    message="",
                    result_type=response_type,
                    media_url=None,
                    media_bytes=content_bytes,
                    media_content_type=content_type or "",
                )
            return CallResult(
                success=False,
                message="接口未返回媒体内容（response_media_from=body 但响应体为空）。",
                result_type="text",
            )
        # url branch
        if response_path and isinstance(data, dict):
            url = _get_nested(data, response_path)
        elif isinstance(data, dict):
            url = data.get("url")
            if url is None and isinstance(data.get("data"), dict):
                url = data["data"].get("url")
        else:
            url = None
        if url and isinstance(url, str):
            return CallResult(
                success=True,
                message="",
                result_type=response_type,
                media_url=url,
            )
        return CallResult(
            success=False,
            message="接口未返回媒体地址或 response_path 未配置。",
            result_type="text",
        )

    out = json.dumps(data if data is not None else text, ensure_ascii=False, indent=2)
    msg = out[:5000] if len(out) > 5000 else out
    return CallResult(success=True, message=msg, result_type="text")
