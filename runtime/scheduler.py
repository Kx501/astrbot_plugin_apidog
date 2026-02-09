# -*- coding: utf-8 -*-
"""Cron-based scheduled API calls. Uses scheduler identity (user_id=scheduler) and core.run()."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..core import run
from ..core.loader import load_schedules
from ..core.log_helper import logger
from ..core.types import CallContext, CallResult

_scheduler: AsyncIOScheduler | None = None
_started: bool = False

SendMessageFn = Callable[[str, CallResult], Awaitable[None]]


def _build_raw_args(api_key: str, args: list[Any], named: dict[str, Any]) -> str:
    parts = [api_key]
    for a in args:
        parts.append(str(a))
    for k, v in named.items():
        v_str = str(v)
        if " " in v_str or '"' in v_str:
            v_str = '"' + v_str.replace("\\", "\\\\").replace('"', '\\"') + '"'
        parts.append(f"{k}={v_str}")
    return " ".join(parts)


async def _run_scheduled(
    data_dir: Path,
    raw_args: str,
    target_session: str | None,
    send_message: SendMessageFn | None,
) -> None:
    ctx = CallContext(user_id="scheduler", group_id=None, is_admin=True)
    result = await run(data_dir, raw_args, ctx, None)
    if not result.success:
        logger.warning("Scheduled call failed: %s", result.message)
    if target_session and send_message:
        try:
            await send_message(target_session, result)
        except Exception:
            logger.exception("Scheduled send_message failed")


def start_scheduler(data_dir: Path, send_message: SendMessageFn | None = None) -> None:
    """Load schedules.json, start AsyncIOScheduler, register cron jobs. Call once at plugin load.
    If called from sync context (e.g. __init__), scheduler is registered but started on first async use.
    """
    global _scheduler, _started
    if _started:
        return
    schedules = load_schedules(data_dir)
    if not schedules:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    _scheduler = AsyncIOScheduler(loop=loop)
    for i, item in enumerate(schedules):
        api_key = item.get("api_key")
        cron = item.get("cron")
        if not api_key or not cron:
            logger.warning("Schedule item %s missing api_key or cron, skip", i)
            continue
        args = item.get("args") if isinstance(item.get("args"), list) else []
        named = item.get("named") if isinstance(item.get("named"), dict) else {}
        raw_args = _build_raw_args(api_key, args or [], named or {})
        target_session = item.get("target_session")
        if isinstance(target_session, str):
            target_session = target_session.strip() or None
        else:
            target_session = None
        job_id = f"apidog_schedule_{i}_{api_key}"
        try:
            trigger = CronTrigger.from_crontab(str(cron).strip())
        except Exception as e:
            logger.warning("Invalid cron %s for schedule %s: %s", cron, job_id, e)
            continue

        def _make_job(
            ddir: Path,
            rargs: str,
            tsession: str | None,
            sfn: SendMessageFn | None,
        ):
            async def _job() -> None:
                await _run_scheduled(ddir, rargs, tsession, sfn)
            return _job

        _scheduler.add_job(
            _make_job(data_dir, raw_args, target_session, send_message),
            trigger,
            id=job_id,
        )
        logger.info("Scheduled job %s: %s at %s", job_id, raw_args, cron)
    _scheduler.start()
    _started = True
