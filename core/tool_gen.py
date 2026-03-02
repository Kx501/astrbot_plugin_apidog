# -*- coding: utf-8 -*-
"""Build LLM function tools from API config (parallel to command_gen for commands).

Invocation method: When the LLM decides to invoke a tool (e.g., weather) during a conversation and fills in parameters args (e.g., “Beijing”),
the framework executes the handler; the handler passes raw_args = api_key + “ ” + args to run(),
following the same logic as when a user sends “/api weather Beijing”. If the API returns images/videos/audio, it sends them to the current session via `send_message`, then returns a description to the LLM.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable

from .log_helper import logger
from .types import CallContext

try:
    from astrbot.core.agent.tool import FunctionTool
    from astrbot.core.agent.run_context import ContextWrapper
    _HAS_ASTRBOT_TOOLS = True
except ImportError:
    _HAS_ASTRBOT_TOOLS = False
    FunctionTool = None  # type: ignore[misc, assignment]
    ContextWrapper = None  # type: ignore[misc, assignment]

try:
    from astrbot.api.event import MessageChain
    from astrbot.api.message_components import Image, Plain, Record, Video
    _HAS_MESSAGE_COMPONENTS = True
except ImportError:
    _HAS_MESSAGE_COMPONENTS = False
    MessageChain = None  # type: ignore[misc, assignment]


def apis_for_llm_tools(apis: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return APIs that are enabled and have as_llm_tool === true (default off)."""
    return [
        a for a in apis
        if a.get("enabled", True) is not False and a.get("as_llm_tool", False) is True
    ]


def _make_handler(data_dir: Path, api_key: str, run_func: Callable[..., Any]) -> Callable[..., Any]:
    """Return an async handler that runs the API via run_func and returns text for the LLM."""

    async def handler(first_arg: Any, **kwargs: Any) -> str:
        # 框架对 handler 传入的是 event（AstrMessageEvent），不是 context；需用 event.send() 发媒体
        args_str = (kwargs.get("args") or "").strip()
        raw_args = f"{api_key} {args_str}".strip()
        user_id: str | None = None
        group_id: str | None = None
        extra_config: dict[str, Any] | None = None
        event = None
        try:
            if hasattr(first_arg, "get_sender_id") and hasattr(first_arg, "send"):
                event = first_arg
                if hasattr(event, "get_sender_id"):
                    try:
                        user_id = str(event.get_sender_id())
                    except Exception:
                        pass
                if hasattr(event, "get_group_id"):
                    try:
                        gid = event.get_group_id()
                        group_id = str(gid) if gid is not None else None
                    except Exception:
                        pass
            else:
                inner = getattr(first_arg, "context", None)
                if inner is not None:
                    event = getattr(inner, "event", None)
                    if event is not None:
                        if hasattr(event, "get_sender_id"):
                            try:
                                user_id = str(event.get_sender_id())
                            except Exception:
                                pass
                        if hasattr(event, "get_group_id"):
                            try:
                                gid = event.get_group_id()
                                group_id = str(gid) if gid is not None else None
                            except Exception:
                                pass
                    ctx = getattr(inner, "context", None)
                    if ctx is not None and hasattr(ctx, "cfg_get"):
                        try:
                            extra_config = ctx.cfg_get("apidog")
                            if not isinstance(extra_config, dict):
                                extra_config = None
                        except Exception:
                            pass
        except Exception:
            pass
        call_ctx = CallContext(user_id=user_id, group_id=group_id)
        result = await run_func(data_dir, raw_args, call_ctx, extra_config)
        if not result.success:
            return result.message or "调用失败"
        if result.result_type == "text":
            return result.message or "(无文本返回)"
        if _HAS_MESSAGE_COMPONENTS and MessageChain is not None and event is not None and hasattr(event, "send"):
            components: list[Any] = []
            temp_paths: list[str] = []
            try:
                if result.result_type == "image" and result.media_url:
                    components = [Image.fromURL(url=result.media_url)]
                elif result.result_type == "video" and result.media_url:
                    components = [Video.fromURL(url=result.media_url)]
                elif result.result_type == "audio" and result.media_url:
                    components = [Record(url=result.media_url)]
                elif result.media_bytes and result.result_type in ("image", "video", "audio"):
                    suffix = ".jpg"
                    if result.media_content_type:
                        if "png" in (result.media_content_type or ""):
                            suffix = ".png"
                        elif "gif" in (result.media_content_type or ""):
                            suffix = ".gif"
                        elif "video" in (result.media_content_type or "") or result.result_type == "video":
                            suffix = ".mp4"
                        elif "audio" in (result.media_content_type or "") or result.result_type == "audio":
                            suffix = ".wav"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                        f.write(result.media_bytes)
                        temp_paths.append(f.name)
                    if result.result_type == "image":
                        components = [Image.fromFileSystem(path=temp_paths[0])]
                    else:
                        components = [Plain(f"（已收到{result.result_type}媒体）")]
                if components:
                    chain = MessageChain(chain=components, type="tool_direct_result")
                    await event.send(chain)
                    for p in temp_paths:
                        Path(p).unlink(missing_ok=True)
                    desc = {"image": "图片", "video": "视频", "audio": "音频"}.get(result.result_type, "媒体")
                    return f"已向用户发送{desc}。"
            except Exception:
                logger.exception("工具发送媒体到会话失败")
                for p in temp_paths:
                    Path(p).unlink(missing_ok=True)
        return result.message or "接口已返回媒体，请告知用户已发送或请其使用指令重试。"

    return handler


def build_llm_tools(
    data_dir: Path,
    apis: list[dict[str, Any]],
    run_func: Callable[..., Any],
    module_path: str | None = None,
) -> list[Any]:
    """
    Build a list of AstrBot FunctionTool instances for APIs with as_llm_tool true.
    run_func should have signature (data_dir, raw_args, context: CallContext, extra_config) -> Awaitable[CallResult].
    module_path is used so the framework can unregister these tools when the plugin is unloaded.
    """
    if not _HAS_ASTRBOT_TOOLS or FunctionTool is None:
        logger.debug("AstrBot FunctionTool not available, skip registering LLM tools")
        return []
    tools: list[Any] = []
    for api in apis_for_llm_tools(apis):
        api_key = api.get("id") or api.get("command") or ""
        if not api_key or not isinstance(api_key, str):
            continue
        desc = (api.get("description") or "").strip() or f"调用接口：{api_key}"
        args_desc = (api.get("args_desc") or api.get("tool_args_desc") or "").strip()
        params = {
            "type": "object",
            "properties": {
                "args": {
                    "type": "string",
                    "description": args_desc,
                },
            },
            "required": [],
        }
        handler = _make_handler(data_dir, api_key, run_func)
        tool = FunctionTool(
            name=api_key,
            description=desc,
            parameters=params,
            handler=handler,
            handler_module_path=module_path,
        )
        tools.append(tool)
    return tools


def register_apidog_llm_tools(
    context: Any,
    data_dir: Path,
    apis: list[dict[str, Any]],
    run_func: Callable[..., Any],
    module_path: str | None = None,
) -> list[Any]:
    """
    Build tools from apis and add them to context (context.add_llm_tools).
    Returns the list of tools added (for optional cleanup).
    """
    tools = build_llm_tools(data_dir, apis, run_func, module_path)
    if not tools:
        return []
    try:
        add_llm_tools = getattr(context, "add_llm_tools", None)
        if add_llm_tools is not None and callable(add_llm_tools):
            add_llm_tools(*tools)
            logger.info("ApiDog 已注册 %d 个 LLM 工具", len(tools))
        else:
            logger.debug("context.add_llm_tools 不可用，跳过注册")
    except Exception:
        logger.exception("注册 ApiDog LLM 工具失败")
    return tools
