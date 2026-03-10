# -*- coding: utf-8 -*-
"""ApiDog config API: FastAPI app for reading/writing config JSON files."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter

from ..core import loader
from ..core.command_gen import inject_commands_into_main, inject_commands_if_changed
from ..core.log_helper import logger
from ..runtime import scheduler as scheduler_mod

_ALLOWED_FILES = frozenset({"config.json", "apis.json", "schedules.json", "groups.json", "auth.json"})

_PROJECT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MAIN_PY_PATH = Path(__file__).resolve().parent.parent / "main.py"

# Brute-force protection: lock out an IP after N failed password attempts
_AUTH_FAIL_MAX = 5
_AUTH_LOCK_SECONDS = 180


def _password_hash(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="ApiDog Config API", version="0.1.0")
    app.state.data_dir = data_dir
    # Read api_pwd_hash from config.json; if missing, not initialized
    _dir = data_dir if data_dir is not None else _PROJECT_DATA_DIR
    if not _dir.is_dir():
        _dir.mkdir(parents=True, exist_ok=True)
    _config_path = _dir / "config.json"
    _raw = {}
    if _config_path.is_file():
        try:
            with open(_config_path, "r", encoding="utf-8") as f:
                _raw = json.load(f)
        except Exception:
            pass
    _raw = _raw if isinstance(_raw, dict) else {}
    _pwd_hash = _raw.get("api_pwd_hash")
    if _pwd_hash and isinstance(_pwd_hash, str) and _pwd_hash.strip():
        app.state.config_password = _pwd_hash.strip()
        app.state.initialized = True
    else:
        app.state.config_password = None
        app.state.initialized = False
    app.state.auth_fail_count = {}
    app.state.auth_lock_until = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["GET", "PUT", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Config-Password"],
    )

    def get_data_dir(request: Request) -> Path:
        injected = getattr(request.app.state, "data_dir", None)
        if injected is not None:
            return injected
        p = _PROJECT_DATA_DIR.resolve()
        if not p.is_dir():
            p.mkdir(parents=True, exist_ok=True)
        return p

    def _client_ip(request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def require_password(request: Request) -> None:
        if not getattr(request.app.state, "initialized", True):
            raise HTTPException(status_code=403, detail="not_initialized")
        ip = _client_ip(request)
        now = time.time()
        lock_until = getattr(request.app.state, "auth_lock_until", {})
        if lock_until.get(ip, 0) > now:
            raise HTTPException(
                status_code=429,
                detail="Too many failed attempts, try again later",
            )
        want = getattr(request.app.state, "config_password", "")
        got = request.headers.get("X-Config-Password", "")
        if not want or got != want:
            fail_count = getattr(request.app.state, "auth_fail_count", {})
            fail_count[ip] = fail_count.get(ip, 0) + 1
            request.app.state.auth_fail_count = fail_count
            if fail_count[ip] >= _AUTH_FAIL_MAX:
                lock_until = getattr(request.app.state, "auth_lock_until", {})
                lock_until[ip] = now + _AUTH_LOCK_SECONDS
                request.app.state.auth_lock_until = lock_until
            raise HTTPException(status_code=401, detail="Invalid or missing password")
        fail_count = getattr(request.app.state, "auth_fail_count", {})
        if ip in fail_count:
            fail_count = dict(fail_count)
            del fail_count[ip]
            request.app.state.auth_fail_count = fail_count
        lock_until = getattr(request.app.state, "auth_lock_until", {})
        if ip in lock_until:
            lock_until = dict(lock_until)
            del lock_until[ip]
            request.app.state.auth_lock_until = lock_until

    def _path_for(name: str, data_dir: Path) -> Path:
        if name not in _ALLOWED_FILES:
            raise HTTPException(status_code=400, detail=f"Invalid resource: {name}")
        return (data_dir / name).resolve()

    def _ensure_inside(base: Path, child: Path) -> bool:
        try:
            child.relative_to(base)
            return True
        except ValueError:
            return False

    def _read_json(path: Path, default: Any) -> Any:
        if not path.is_file():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read {path.name}: {e}") from e

    def _trigger_plugin_reload(request: Request) -> None:
        """If reload_trigger is set, schedule a plugin self-reload on the main loop (non-blocking).
        Delay ~3s before reload so the response can be sent before the process exits.
        """
        trigger = getattr(request.app.state, "reload_trigger", None)
        if not trigger:
            return
        try:
            pm, plugin_name, loop = trigger

            async def _delayed_reload() -> None:
                await asyncio.sleep(3)
                await pm.reload(plugin_name)

            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(_delayed_reload(), loop=loop)
            )
        except Exception:
            logger.exception("Failed to schedule plugin reload")

    def _write_json_atomic(path: Path, data: Any) -> None:
        base = path.parent
        base.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=base, prefix=".", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception as e:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise HTTPException(status_code=500, detail=f"Failed to write {path.name}: {e}") from e

    router = APIRouter()

    @router.get("/status")
    def get_status(request: Request) -> dict[str, bool]:
        """No auth required. Returns whether api_pwd_hash is set (initialized)."""
        return {"initialized": getattr(request.app.state, "initialized", False)}

    @router.post("/init")
    def post_init(
        request: Request,
        body: dict[str, Any] = Body(...),
        data_dir: Path = Depends(get_data_dir),
    ) -> dict[str, str]:
        """Only when not initialized. Writes password hash to api_pwd_hash (no plain text)."""
        if getattr(request.app.state, "initialized", False):
            raise HTTPException(status_code=400, detail="already_initialized")
        pwd = body.get("password")
        if not isinstance(pwd, str) or not pwd.strip():
            raise HTTPException(status_code=400, detail="password required")
        path = _path_for("config.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        raw = _read_json(path, {})
        if not isinstance(raw, dict):
            raw = {}
        pwd_plain = pwd.strip()
        raw["api_pwd_hash"] = _password_hash(pwd_plain)
        _write_json_atomic(path, raw)
        loader.invalidate_config(data_dir)
        request.app.state.config_password = raw["api_pwd_hash"]
        request.app.state.initialized = True
        return {"status": "ok"}

    @router.put("/password")
    def put_password(
        request: Request,
        body: dict[str, Any] = Body(...),
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> dict[str, str]:
        """Change api_pwd_hash when authenticated. Body: { new_password: "..." }."""
        new_pwd = body.get("new_password")
        if not isinstance(new_pwd, str) or not new_pwd.strip():
            raise HTTPException(status_code=400, detail="new_password required")
        path = _path_for("config.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        raw = _read_json(path, {})
        if not isinstance(raw, dict):
            raw = {}
        raw["api_pwd_hash"] = _password_hash(new_pwd.strip())
        _write_json_atomic(path, raw)
        request.app.state.config_password = raw["api_pwd_hash"]
        return {"status": "ok"}

    @router.get("/config")
    def get_config(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> Any:
        path = _path_for("config.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        return _read_json(path, {})

    @router.put("/config")
    def put_config(
        request: Request,
        body: dict[str, Any] = Body(...),
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> dict[str, str]:
        path = _path_for("config.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Body must be a JSON object")
        _write_json_atomic(path, body)
        loader.invalidate_config(data_dir)
        try:
            apis = loader.load_apis(data_dir)
            inject_commands_if_changed(_MAIN_PY_PATH, apis)
            _trigger_plugin_reload(request)
        except Exception:
            logger.exception("Failed to inject commands into main after PUT config")
        return {"status": "ok"}

    @router.get("/apis")
    def get_apis(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> list[Any]:
        return loader.load_apis(data_dir)

    @router.put("/apis")
    def put_apis(
        request: Request,
        body: dict[str, Any] = Body(...),
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> dict[str, str]:
        if not isinstance(body, dict) or "apis" not in body:
            raise HTTPException(status_code=400, detail='Body must be {"apis": [...]}')
        if not isinstance(body["apis"], list):
            raise HTTPException(status_code=400, detail="apis must be an array")
        path = _path_for("apis.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        old_apis = loader.load_apis(data_dir)
        _write_json_atomic(path, {"apis": body["apis"]})
        loader.invalidate_apis(data_dir)
        try:
            block_changed = inject_commands_if_changed(_MAIN_PY_PATH, body["apis"])
            old_llm = set(
                (a.get("id") or a.get("command") or "")
                for a in old_apis
                if a.get("as_tool") is True
            )
            new_llm = set(
                (a.get("id") or a.get("command") or "")
                for a in body["apis"]
                if a.get("as_tool") is True
            )
            if block_changed or old_llm != new_llm:
                _trigger_plugin_reload(request)
        except Exception:
            logger.exception("Failed to inject commands into main after PUT apis")
        return {"status": "ok"}

    @router.get("/schedules")
    def get_schedules(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> list[Any]:
        return loader.load_schedules(data_dir)

    @router.put("/schedules")
    def put_schedules(
        body: dict[str, Any] = Body(...),
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> dict[str, str]:
        if not isinstance(body, dict) or "schedules" not in body:
            raise HTTPException(status_code=400, detail='Body must be {"schedules": [...]}')
        if not isinstance(body["schedules"], list):
            raise HTTPException(status_code=400, detail="schedules must be an array")
        path = _path_for("schedules.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        _write_json_atomic(path, {"schedules": body["schedules"]})
        # Hot reload: refresh scheduled tasks after save
        try:
            scheduler_mod.reload_schedules(data_dir)
        except Exception:
            logger.exception("Failed to reload schedules after PUT")
        return {"status": "ok"}

    @router.get("/groups")
    def get_groups(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> Any:
        return loader.load_groups(data_dir)

    @router.put("/groups")
    def put_groups(
        body: dict[str, Any] = Body(...),
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> dict[str, str]:
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Body must be a JSON object")
        path = _path_for("groups.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        _write_json_atomic(path, body)
        loader.invalidate_groups(data_dir)
        return {"status": "ok"}

    @router.get("/auth")
    def get_auth(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> Any:
        return loader.load_auth(data_dir)

    @router.put("/auth")
    def put_auth(
        body: dict[str, Any] = Body(...),
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> dict[str, str]:
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Body must be a JSON object")
        path = _path_for("auth.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        _write_json_atomic(path, body)
        loader.invalidate_auth(data_dir)
        return {"status": "ok"}

    app.include_router(router, prefix="/api")

    dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if dist_dir.is_dir() and (dist_dir / "index.html").is_file():
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static_assets")
        index_path = dist_dir / "index.html"

        def _safe_relative_to(base: Path, child: Path) -> bool:
            try:
                child.relative_to(base)
                return True
            except ValueError:
                return False

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            if not full_path or full_path.startswith("api/") or full_path.startswith("assets/"):
                return FileResponse(index_path, media_type="text/html")
            safe = (dist_dir / full_path).resolve()
            if safe.is_file() and _safe_relative_to(dist_dir, safe):
                return FileResponse(safe)
            return FileResponse(index_path, media_type="text/html")

    return app
