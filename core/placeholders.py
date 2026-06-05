# -*- coding: utf-8 -*-
"""Scan API config for {{key}} / {{key|default}} placeholders."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PLACEHOLDER_RE = re.compile(r"\{\{([^}|]+)(?:\|([^}]*))?\}\}")

_API_FIELDS = ("url", "headers", "params", "body")


@dataclass(frozen=True)
class ParamSpec:
    name: str
    default: str | None

    @property
    def optional(self) -> bool:
        return self.default is not None


def _scan_value(value: Any, found: dict[str, str | None]) -> None:
    if isinstance(value, str):
        for m in PLACEHOLDER_RE.finditer(value):
            key = m.group(1).strip()
            if not key:
                continue
            default = m.group(2)
            if default is not None:
                default = default.strip()
            if key not in found:
                found[key] = default
            elif found[key] is None and default is not None:
                found[key] = default
        return
    if isinstance(value, dict):
        for k, v in value.items():
            _scan_value(k, found)
            _scan_value(v, found)
        return
    if isinstance(value, list):
        for v in value:
            _scan_value(v, found)


def infer_tool_params(api: dict[str, Any]) -> list[ParamSpec]:
    """Return placeholders in url → headers → params → body scan order (first occurrence wins)."""
    found: dict[str, str | None] = {}
    for field in _API_FIELDS:
        _scan_value(api.get(field), found)
    return [ParamSpec(name=k, default=v) for k, v in found.items()]


def infer_param_names(api: dict[str, Any]) -> list[str]:
    return [s.name for s in infer_tool_params(api)]
