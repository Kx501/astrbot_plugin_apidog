# -*- coding: utf-8 -*-
"""Build help message for /api help and /api help <接口名>."""

from __future__ import annotations

import re
from typing import Any

from . import loader


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
    lines = ["用法: /api <接口名> [参数...]", ""]
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

    params = api.get("params") or {}
    pos_names, named_optional, named_required = _infer_params(params)
    if pos_names or named_optional or named_required:
        parts = []
        if pos_names:
            parts.append(", ".join(pos_names))
        all_named = list(named_required) + [f"{k}(可选)" for k in named_optional]
        if all_named:
            parts.append(", ".join(all_named))
        lines.append("参数: " + "；".join(parts))
    else:
        lines.append("参数: 无")
    lines.append("")

    example = _build_example(command, params)
    lines.append("示例: " + example)
    return "\n".join(lines)


_PLACEHOLDER_ARGS = re.compile(r"\{\{args\.(\d+)\}\}")
_PLACEHOLDER_NAMED = re.compile(r"\{\{named\.([^}|]+)(?:\|([^}]*))?\}\}")


def _infer_params(params: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Return (positional_names_in_order, optional_named_keys, required_named_keys)."""
    positional: dict[int, str] = {}
    named_optional: list[str] = []
    named_required: list[str] = []
    seen_named: set[str] = set()

    for key, val in (params or {}).items():
        s = str(val) if val is not None else ""
        m_args = _PLACEHOLDER_ARGS.search(s)
        m_named = _PLACEHOLDER_NAMED.search(s)
        if m_args:
            idx = int(m_args.group(1))
            positional[idx] = key
        elif m_named:
            name = m_named.group(1).strip()
            default = m_named.group(2)
            if name not in seen_named:
                seen_named.add(name)
                if default is not None:
                    named_optional.append(name)
                else:
                    named_required.append(name)

    pos_names = [positional[i] for i in sorted(positional.keys())]
    return pos_names, named_optional, named_required


def _build_example(command: str, params: dict[str, Any]) -> str:
    pos_names, named_optional, named_required = _infer_params(params)
    if not pos_names and not named_required and not named_optional:
        return f"/api {command}"
    if pos_names:
        example_args = " ".join([f"<{n}>" for n in pos_names])
        base = f"/api {command} {example_args}".strip()
    else:
        base = f"/api {command}"
    named_parts = [f"{k}=<值>" for k in named_required + named_optional]
    if named_parts:
        return f"{base} 或 {base} {' '.join(named_parts)}"
    return base
