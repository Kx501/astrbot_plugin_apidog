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
_data_dir: Path | None = None
_send_message: "SendMessageFn | None" = None

_JOB_ID_PREFIX = "apidog_schedule_"

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
    ctx = CallContext(user_id="scheduler", group_id=None)
    result = await run(data_dir, raw_args, ctx, None)
    if not result.success:
        logger.warning("Scheduled call failed: %s", result.message)
    if target_session and send_message:
        try:
            await send_message(target_session, result)
        except Exception:
            logger.exception("Scheduled send_message failed")


def _get_loop_or_none() -> asyncio.AbstractEventLoop | None:
    """Get an asyncio loop suitable for AsyncIOScheduler. Return None if unavailable."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            return None


def _register_jobs(
    scheduler: AsyncIOScheduler,
    data_dir: Path,
    schedules: list[dict],
    send_message: SendMessageFn | None,
) -> None:
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
        job_id = f"{_JOB_ID_PREFIX}{i}_{api_key}"
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

        scheduler.add_job(
            _make_job(data_dir, raw_args, target_session, send_message),
            trigger,
            id=job_id,
        )
        logger.info("Scheduled job %s: %s at %s", job_id, raw_args, cron)


def start_scheduler(data_dir: Path, send_message: SendMessageFn | None = None) -> None:
    """Load schedules.json, start AsyncIOScheduler, register cron jobs. Call once at plugin load.
    If called from sync context (e.g. __init__), scheduler is registered but started on first async use.
    """
    global _scheduler, _started, _data_dir, _send_message
    _data_dir = data_dir
    _send_message = send_message
    if _started:
        return
    loop = _get_loop_or_none()
    if loop is None:
        logger.warning("No asyncio event loop found; scheduler disabled")
        return
    _scheduler = AsyncIOScheduler(loop=loop)
    schedules = load_schedules(data_dir)
    if schedules:
        _register_jobs(_scheduler, data_dir, schedules, send_message)
    _scheduler.start()
    _started = True


def reload_schedules(data_dir: Path) -> None:
    """Reload schedules.json and refresh cron jobs. Safe to call after PUT /api/schedules."""
    global _scheduler, _started, _data_dir
    _data_dir = data_dir
    schedules = load_schedules(data_dir)

    if _scheduler is None:
        # Scheduler was never started (e.g. plugin started with empty schedules, or standalone API mode).
        # Try to start it if possible; otherwise no-op.
        start_scheduler(data_dir, _send_message)
        return

    # Remove all ApiDog jobs, then re-add according to latest schedules.
    try:
        for job in _scheduler.get_jobs():
            try:
                if str(job.id).startswith(_JOB_ID_PREFIX):
                    _scheduler.remove_job(job.id)
            except Exception:
                logger.exception("Failed to remove job %s", getattr(job, "id", ""))
    except Exception:
        logger.exception("Failed to enumerate scheduler jobs")

    if schedules:
        _register_jobs(_scheduler, data_dir, schedules, _send_message)

    # Ensure scheduler is started (in case it was created but not started).
    if not _started:
        try:
            _scheduler.start()
        except Exception:
            logger.exception("Failed to start scheduler during reload")
        _started = True
