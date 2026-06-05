# -*- coding: utf-8 -*-
"""Parse command args with quote support and key=value."""

import re
from typing import Any

from .placeholders import PLACEHOLDER_RE


def parse_args(raw: str) -> tuple[list[str], dict[str, str]]:
    """
    Parse raw string into positional args (list) and named args (dict).
    - Quoted segments (single or double) become one arg.
    - key=value (value may be quoted) go into named.
    - Escaping: \\" and \\' inside quotes; "" or '' for literal quote.
    """
    args: list[str] = []
    named: dict[str, str] = {}
    if not raw or not raw.strip():
        return args, named

    tokens = _tokenize(raw.strip())
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if "=" in t and not t.startswith("="):
            key, _, rest = t.partition("=")
            key = key.strip()
            if key and (rest.startswith('"') or rest.startswith("'")):
                value = _strip_quotes(rest)
                named[key] = value
            elif key:
                named[key] = rest
            i += 1
        else:
            args.append(t)
            i += 1
    return args, named


def _tokenize(s: str) -> list[str]:
    """Split by space, respecting double and single quotes."""
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        while i < n and s[i] in " \t":
            i += 1
        if i >= n:
            break
        if s[i] in "\"'":
            q = s[i]
            i += 1
            parts = []
            while i < n:
                if s[i] == "\\" and i + 1 < n and s[i + 1] in "\"'":
                    parts.append(s[i + 1])
                    i += 2
                    continue
                if s[i] == q:
                    if i + 1 < n and s[i + 1] == q:
                        parts.append(q)
                        i += 2
                        continue
                    i += 1
                    break
                parts.append(s[i])
                i += 1
            out.append("".join(parts))
            continue
        start = i
        while i < n and s[i] not in " \t":
            if s[i] in "\"'":
                break
            i += 1
        out.append(s[start:i])
    return out


def _strip_quotes(s: str) -> str:
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        inner = s[1:-1].replace('\\"', '"').replace("\\'", "'").replace('""', '"').replace("''", "'")
        return inner
    return s


def resolve_placeholders(value: Any, named: dict[str, str]) -> Any:
    """Recursively replace {{key}}, {{key|default}} in strings/dicts/lists."""
    if isinstance(value, str):
        return _replace_placeholders_str(value, named)
    if isinstance(value, dict):
        return {k: resolve_placeholders(v, named) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_placeholders(v, named) for v in value]
    return value


def _replace_placeholders_str(s: str, named: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        default = m.group(2)
        if default is not None:
            default = default.strip()
        return named.get(key, default if default is not None else "")

    return PLACEHOLDER_RE.sub(repl, s)
