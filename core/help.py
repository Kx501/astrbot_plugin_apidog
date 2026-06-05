# -*- coding: utf-8 -*-
"""Build help message for /api help and /api help <接口名>."""

from __future__ import annotations

from typing import Any

from . import loader
from .placeholders import infer_tool_params


def build_help_message(apis: list[dict], target: str | None = None) -> str:
    """
    target is None or empty: list all APIs (command - name, optional description).
    target set: detail for one API (name, command, optional help_text, params, example).
    """
    if not target or not (target := target.strip()):
        return _build_list(apis)

    api = loader.find_api_by_id_or_command(apis, target)
    if not api:
        return f"未找到接口: {target}。"
    return _build_detail(api)


def _build_list(apis: list[dict]) -> str:
    lines = ["用法: /api <接口名> [键=值 ...]", ""]
    for api in apis:
        cmd = api.get("command") or api.get("id") or "?"
        name = api.get("name") or cmd
        desc = api.get("description")
        if desc and isinstance(desc, str):
            lines.append(f"· {cmd} - {name}：{desc}")
        else:
            lines.append(f"· {cmd} - {name}")
    return "\n".join(lines)


def _build_detail(api: dict) -> str:
    name = api.get("name") or api.get("id") or "?"
    command = api.get("command") or api.get("id") or "?"
    lines = [f"【{name}】", f"命令: {command}", ""]

    help_text = api.get("help_text") or api.get("help")
    if help_text and isinstance(help_text, str):
        lines.append(help_text.strip())
        lines.append("")

    specs = infer_tool_params(api)
    if specs:
        required = [s.name for s in specs if not s.optional]
        optional = [s.name for s in specs if s.optional]
        parts: list[str] = []
        if required:
            parts.append(", ".join(required))
        if optional:
            parts.append(", ".join(f"{k}(可选)" for k in optional))
        lines.append("参数: " + "；".join(parts))
    else:
        lines.append("参数: 无")
    lines.append("")

    example = _build_example(command, api)
    lines.append("示例: " + example)
    return "\n".join(lines)


def _build_example(command: str, api: dict[str, Any]) -> str:
    specs = infer_tool_params(api)
    if not specs:
        return f"/api {command}"
    named_parts = [f"{s.name}=<值>" for s in specs]
    return f"/api {command} {' '.join(named_parts)}"
