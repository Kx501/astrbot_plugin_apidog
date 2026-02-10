# -*- coding: utf-8 -*-
"""ApiDog AstrBot entry. Plugin class must live in main.py per AstrBot docs."""

from __future__ import annotations

import threading
import tempfile
from pathlib import Path
from typing import Any, List

import uvicorn
from astrbot.api import logger as _ab_logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star, StarTools, register
from astrbot.api.message_components import Image, Plain, Record, Video

from .api import create_app
from .core import CallContext, CallResult, run
from .core.loader import get_api_port
from .core.log_helper import set_apidog_logger
from .runtime import start_scheduler


@register(
    "ApiDog",
    "可配置 API 与指令绑定，通过指令调用 API。用法: /api <接口名> [参数...]",
    "0.1.0",
    "https://github.com/Kx501/astrbot_plugin_apidog",
)
class ApiDogStar(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        set_apidog_logger(_ab_logger)
        self._data_dir = Path(StarTools.get_data_dir(None))
        start_scheduler(self._data_dir, send_message=self._send_scheduled_result)
        api_app = create_app(self._data_dir)
        port = get_api_port(self._data_dir)
        config = uvicorn.Config(
            api_app, host="0.0.0.0", port=port, access_log=False
        )
        self._uvicorn_server = uvicorn.Server(config)
        self._uvicorn_thread = threading.Thread(target=self._uvicorn_server.run, daemon=True)
        self._uvicorn_thread.start()

    async def terminate(self) -> None:
        """Plugin unload: stop uvicorn to release the configured API port."""
        if getattr(self, "_uvicorn_server", None) is not None:
            self._uvicorn_server.should_exit = True
            thread = getattr(self, "_uvicorn_thread", None)
            if thread is not None and thread.is_alive():
                thread.join(timeout=3.0)

    def _result_to_chain(self, result: CallResult) -> tuple[List[Any], List[str]]:
        """Build AstrBot message chain from CallResult; second return is list of temp file paths to delete after send."""
        if result.result_type == "text":
            return [Plain(result.message or "")], []
        if result.result_type == "image" and result.media_url:
            return [Image.fromURL(url=result.media_url)], []
        if result.result_type == "video" and result.media_url:
            return [Video.fromURL(url=result.media_url)], []
        if result.result_type == "audio" and result.media_url:
            return [Record(url=result.media_url)], []
        if result.media_bytes and result.result_type in ("image", "video", "audio"):
            suffix = ".jpg"
            if result.media_content_type:
                if "png" in result.media_content_type:
                    suffix = ".png"
                elif "gif" in result.media_content_type:
                    suffix = ".gif"
                elif "video" in result.media_content_type or result.result_type == "video":
                    suffix = ".mp4"
                elif "audio" in result.media_content_type or result.result_type == "audio":
                    suffix = ".wav"
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                    f.write(result.media_bytes)
                    tmp_path = f.name
                if result.result_type == "image":
                    return [Image.fromFileSystem(path=tmp_path)], [tmp_path]
                return [Plain(f"（媒体已收到，{result.result_type}）")], [tmp_path]
            except Exception:
                return [Plain("媒体已收到，发送暂不支持。")], []
        return [Plain(result.message or "")], []

    async def _send_scheduled_result(self, target_session: str, result: CallResult) -> None:
        """Send scheduled task result to target session (AstrBot: unified_msg_origin)."""
        components, tmp_paths = self._result_to_chain(result)
        message_chain = MessageChain(chain=components)
        try:
            await self.context.send_message(target_session, message_chain)
        finally:
            for p in tmp_paths:
                Path(p).unlink(missing_ok=True)

    @filter.command("api")
    async def cmd_api(self, event: AstrMessageEvent) -> None:
        """通过接口名调用配置的 API。用法: /api <接口名> [参数...]，例如 /api 天气 北京"""
        raw = event.message_str.strip()
        for prefix in ("/api ", "/api\t", "api ", "api\t"):
            if raw.startswith(prefix):
                raw = raw[len(prefix) :].strip()
                break
        if raw.startswith("/api") and len(raw) > 4:
            raw = raw[4:].strip()
        if not raw:
            yield event.plain_result("用法: /api <接口名> [参数...]，例如 /api 天气 北京")
            return

        try:
            user_id = str(event.get_sender_id())
        except Exception:
            user_id = None
        try:
            gid = event.get_group_id()
            group_id = str(gid) if gid is not None else None
        except Exception:
            group_id = None
        ctx = CallContext(user_id=user_id, group_id=group_id)

        extra_config: dict[str, Any] | None = None
        try:
            cfg = self.context.cfg_get("apidog")
            if isinstance(cfg, dict):
                extra_config = cfg
        except Exception:
            pass

        result = await run(self._data_dir, raw, ctx, extra_config)

        if not result.success:
            yield event.plain_result(result.message)
            return

        if result.result_type == "text":
            yield event.plain_result(result.message)
            return

        # 媒体：优先 URL，否则用 media_bytes（写临时文件后发）
        if result.media_url:
            if result.result_type == "image":
                yield event.image_result(result.media_url)
                return
            if result.result_type == "video":
                try:

                    yield event.chain_result([Video.fromURL(url=result.media_url)])
                except Exception:
                    yield event.plain_result(f"视频链接: {result.media_url}")
                return
            if result.result_type == "audio":
                try:

                    yield event.chain_result([Record(url=result.media_url)])
                except Exception:
                    yield event.plain_result(f"音频链接: {result.media_url}")
                return

        if result.media_bytes and result.result_type in ("image", "video", "audio"):
            suffix = ".jpg"
            if result.media_content_type:
                if "png" in result.media_content_type:
                    suffix = ".png"
                elif "gif" in result.media_content_type:
                    suffix = ".gif"
                elif "video" in result.media_content_type or result.result_type == "video":
                    suffix = ".mp4"
                elif "audio" in result.media_content_type or result.result_type == "audio":
                    suffix = ".wav"
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                    f.write(result.media_bytes)
                    tmp_path = f.name
                try:
                    if result.result_type == "image":
                        yield event.chain_result([Image.fromFileSystem(path=tmp_path)])
                    else:
                        yield event.plain_result(f"（媒体已收到，{result.result_type} 从字节发送暂用链接或文件）")
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                yield event.plain_result("媒体内容已收到，但当前平台暂不支持从字节发送。")
            return

        yield event.plain_result(result.message)
