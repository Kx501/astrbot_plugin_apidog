# -*- coding: utf-8 -*-
"""ApiDog config API: FastAPI app for reading/writing config JSON files."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter

from ..core import loader
from ..core.command_gen import inject_commands_into_main
from ..core.log_helper import logger
from ..runtime import scheduler as scheduler_mod

_ALLOWED_FILES = frozenset({"config.json", "apis.json", "schedules.json", "groups.json", "auth.json"})

_PROJECT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MAIN_PY_PATH = Path(__file__).resolve().parent.parent / "main.py"


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="ApiDog Config API", version="0.1.0")
    app.state.data_dir = data_dir
    app.state.config_password = secrets.token_hex(8)
    logger.info("Config API 临时密码: %s", app.state.config_password)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["GET", "PUT", "OPTIONS"],
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

    def require_password(request: Request) -> None:
        want = getattr(request.app.state, "config_password", "")
        got = request.headers.get("X-Config-Password", "")
        if not want or got != want:
            raise HTTPException(status_code=401, detail="Invalid or missing password")

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
            inject_commands_into_main(
                _MAIN_PY_PATH, apis, bool(body.get("register_commands", False))
            )
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
        _write_json_atomic(path, {"apis": body["apis"]})
        loader.invalidate_apis(data_dir)
        try:
            cfg = loader.load_config(data_dir)
            inject_commands_into_main(
                _MAIN_PY_PATH, body["apis"], bool(cfg.get("register_commands", False))
            )
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
        # 热重载：保存后立即刷新定时任务
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


app = create_app()
