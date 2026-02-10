# -*- coding: utf-8 -*-
"""ApiDog core types: CallContext, CallResult, ResultType."""

from __future__ import annotations

from typing import Literal

ResultType = Literal["text", "image", "video", "audio"]


class CallContext:
    """Platform-agnostic call context for permission and placeholders."""

    __slots__ = ("user_id", "group_id")

    def __init__(
        self,
        user_id: str | None = None,
        group_id: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.group_id = group_id


class CallResult:
    """Unified result for any platform to send as text or media."""

    __slots__ = (
        "success",
        "message",
        "result_type",
        "media_url",
        "media_bytes",
        "media_content_type",
    )

    def __init__(
        self,
        success: bool,
        message: str = "",
        result_type: ResultType = "text",
        media_url: str | None = None,
        media_bytes: bytes | None = None,
        media_content_type: str | None = None,
    ) -> None:
        self.success = success
        self.message = message
        self.result_type = result_type
        self.media_url = media_url
        self.media_bytes = media_bytes
        self.media_content_type = media_content_type
