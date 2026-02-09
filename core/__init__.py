# -*- coding: utf-8 -*-
"""ApiDog core: run() orchestration and re-exports."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from .parse_args import parse_args, resolve_placeholders
from .types import CallContext, CallResult
from . import help as help_mod
from . import loader
from . import permission
from . import rate_limit as rate_limit_mod
from . import request as req_mod
from . import response

logger = logging.getLogger("apidog.core")

__all__ = ["run", "CallContext", "CallResult"]


def _log_call(
    api_key: str,
    context: CallContext,
    success: bool,
    status_code: int | None = None,
    error_type: str | None = None,
) -> None:
    """Mixed-dimension call log: caller (user_id, group_id) + callee (api_key) + result."""
    parts = [
        "ApiDog call",
        f"api_key={api_key or ''}",
        f"user_id={context.user_id or ''}",
        f"group_id={context.group_id or ''}",
        f"success={str(success).lower()}",
    ]
    if status_code is not None:
        parts.append(f"status_code={status_code}")
    if error_type:
        parts.append(f"error={error_type}")
    logger.info(" ".join(parts))


async def run(
    data_dir: Path,
    raw_args: str,
    context: CallContext,
    extra_config: dict[str, Any] | None = None,
) -> CallResult:
    """
    Load config, resolve API by first token in raw_args, check permission,
    build request, execute, parse response. Returns a platform-agnostic CallResult.
    """
    apis = loader.load_apis(data_dir)
    apis = loader.enabled_apis(apis)
    auth = loader.load_auth(data_dir)
    groups = loader.load_groups(data_dir)
    global_config = loader.load_config(data_dir)

    args, named = parse_args(raw_args.strip())
    if not args:
        _log_call("", context, False)
        return CallResult(success=False, message="请提供接口名（第一个参数）。", result_type="text")
    api_key = args[0]
    rest_args = args[1:]

    if api_key == "help":
        target = args[1] if len(args) > 1 else None
        message = help_mod.build_help_message(apis, target)
        _log_call(api_key, context, True)
        return CallResult(success=True, message=message, result_type="text")

    api = loader.find_api(apis, api_key)
    if not api:
        _log_call(api_key, context, False)
        return CallResult(
            success=False,
            message=f"未找到接口: {api_key}。可用接口请在配置中查看。",
            result_type="text",
        )

    ok, err = permission.check_permission(api, context, groups)
    if not ok:
        _log_call(api_key, context, False)
        return CallResult(success=False, message=err, result_type="text")

    ok, err = rate_limit_mod.check_and_record_global(api, api_key)
    if not ok:
        _log_call(api_key, context, False, error_type="rate_limit")
        return CallResult(success=False, message=err, result_type="text")
        
    ok, err = rate_limit_mod.check_and_record(api, context.user_id, api_key)
    if not ok:
        _log_call(api_key, context, False, error_type="rate_limit")
        return CallResult(success=False, message=err, result_type="text")

    config = loader.get_config_for_placeholders(auth, extra_config)
    url = api.get("url") or ""
    if not url:
        _log_call(api_key, context, False)
        return CallResult(success=False, message="该接口未配置 URL。", result_type="text")

    method = (api.get("method") or "GET").upper()
    headers = dict(api.get("headers") or {})
    params = dict(api.get("params") or {})
    body_raw = api.get("body")

    headers = resolve_placeholders(headers, rest_args, named, config)
    params = resolve_placeholders(params, rest_args, named, config)
    url = resolve_placeholders(url, rest_args, named, config)
    if isinstance(body_raw, (dict, list)):
        body = resolve_placeholders(body_raw, rest_args, named, config)
    elif isinstance(body_raw, str):
        body = resolve_placeholders(body_raw, rest_args, named, config)
    else:
        body = body_raw

    client_opts = loader.merge_client_options(global_config, api)
    timeout_seconds = client_opts.get("timeout_seconds", 30.0)
    retry_cfg = client_opts.get("retry")
    max_attempts = retry_cfg.get("max_attempts", 0) if isinstance(retry_cfg, dict) else 0
    backoff_seconds = retry_cfg.get("backoff_seconds", 1.0) if isinstance(retry_cfg, dict) else 1.0
    retryable_statuses = {500, 502, 503, 429}

    status_code, data, text, content_bytes, content_type = None, None, "", None, None

    for attempt in range(1 + max_attempts):
        try:
            status_code, data, text, content_bytes, content_type = await req_mod.execute_request(
                api, url, method, headers, params, body, auth, timeout=timeout_seconds
            )
            if status_code in retryable_statuses and attempt < max_attempts:
                await asyncio.sleep(backoff_seconds)
                continue
            break
        except httpx.TimeoutException:
            last_timeout = True
            if attempt < max_attempts:
                await asyncio.sleep(backoff_seconds)
                continue
            _log_call(api_key, context, False, error_type="timeout")
            return CallResult(success=False, message="请求超时。", result_type="text")
        except Exception:
            logger.exception("ApiDog request error")
            _log_call(api_key, context, False, error_type="error")
            return CallResult(success=False, message="请求出错，请稍后重试。", result_type="text")

    result = response.parse_response(api, status_code, data, text, content_bytes, content_type)
    _log_call(api_key, context, result.success, status_code=status_code)
    return result
