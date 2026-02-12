# -*- coding: utf-8 -*-
"""Generate command code: inject into main.py."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .log_helper import logger

_BEGIN_MARKER = "# --- BEGIN GENERATED COMMANDS ---"
_END_MARKER = "# --- END GENERATED COMMANDS ---"


def _escape(s: str) -> str:
    """Escape for use inside double-quoted Python string."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def _safe_method_name(index: int) -> str:
    """Valid Python method name for generated command handler."""
    return f"cmd_{index}"


def _build_main_class_methods(apis: list[dict[str, Any]]) -> str:
    """Build the method lines to inject into ApiDogStar (4-space indent for class body)."""
    enabled = [a for a in apis if a.get("enabled", True) is not False]
    lines: list[str] = []
    for i, api in enumerate(enabled):
        cmd_name = api.get("command") or api.get("id") or ""
        if not cmd_name or not isinstance(cmd_name, str):
            continue
        api_key = api.get("id") or api.get("command") or cmd_name
        if not isinstance(api_key, str):
            continue
        cmd_esc = _escape(cmd_name)
        api_key_esc = _escape(api_key)
        method = _safe_method_name(i)
        desc = (api.get("description") or "").strip().replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
        lines.append(f'    @filter.command("{cmd_esc}")')
        lines.append(f"    async def {method}(self, event):")
        lines.append(f'        """{desc}"""')
        lines.append("        raw = event.message_str.strip()")
        lines.append(f'        for prefix in ("/{cmd_esc} ", "{cmd_esc} "):')
        lines.append("            if raw.startswith(prefix):")
        lines.append("                raw = raw[len(prefix):].strip()")
        lines.append("                break")
        lines.append(f'        if raw.startswith("/{cmd_esc}"):')
        lines.append(f'            raw = raw[1 + len("{cmd_esc}"):].strip()')
        lines.append("        try:")
        lines.append("            user_id = str(event.get_sender_id())")
        lines.append("        except Exception:")
        lines.append("            user_id = None")
        lines.append("        try:")
        lines.append("            gid = event.get_group_id()")
        lines.append("            group_id = str(gid) if gid is not None else None")
        lines.append("        except Exception:")
        lines.append("            group_id = None")
        lines.append("        ctx = CallContext(user_id=user_id, group_id=group_id)")
        lines.append("        extra_config = None")
        lines.append("        try:")
        lines.append('            cfg = self.context.cfg_get("apidog")')
        lines.append("            if isinstance(cfg, dict):")
        lines.append("                extra_config = cfg")
        lines.append("        except Exception:")
        lines.append("            pass")
        lines.append(f'        raw_args = "{api_key_esc}" + (" " + raw if raw else "")')
        lines.append("        async for x in self._run_and_send(event, raw_args, ctx, extra_config):")
        lines.append("            yield x")
        lines.append("")
    return "\n".join(lines) if lines else "    pass"


def block_content_is_pass(main_path: Path) -> bool:
    """True if the GENERATED COMMANDS block contains only 'pass' (e.g. first load after update)."""
    if not main_path.is_file():
        return False
    text = main_path.read_text(encoding="utf-8")
    begin = "    " + _BEGIN_MARKER
    end = "    " + _END_MARKER
    pattern = re.compile(
        re.escape(begin) + r"(.*?)" + re.escape(end),
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return False
    inner = m.group(1).strip()
    return inner == "pass"


def inject_commands_into_main(
    main_path: Path,
    apis: list[dict[str, Any]],
    register_enabled: bool,
) -> None:
    """Replace the GENERATED COMMANDS block in main.py and clear __pycache__ for main."""
    if not main_path.is_file():
        return
    text = main_path.read_text(encoding="utf-8")
    begin = "    " + _BEGIN_MARKER
    end = "    " + _END_MARKER
    pattern = re.compile(
        re.escape(begin) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    if not pattern.search(text):
        return
    if register_enabled:
        inner = _build_main_class_methods(apis)
    else:
        inner = "    pass"
    block = f"    {_BEGIN_MARKER}\n{inner}\n    {_END_MARKER}"
    new_text = pattern.sub(block, text, count=1)
    if new_text == text:
        return
    main_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = None, None
    try:
        import tempfile
        import os
        fd, tmp = tempfile.mkstemp(dir=main_path.parent, prefix=".main.", suffix=".py")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp, main_path)
    except Exception:
        if fd is not None and tmp is not None:
            try:
                import os
                os.unlink(tmp)
            except OSError:
                pass
        raise
    cache_dir = main_path.parent / "__pycache__"
    if cache_dir.is_dir():
        for f in cache_dir.glob("main.*.pyc"):
            f.unlink(missing_ok=True)
    logger.info("独立指令已注入 main.py，请手动完成插件重载")
