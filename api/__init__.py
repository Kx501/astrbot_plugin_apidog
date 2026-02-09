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
from fastapi.staticfiles import StaticFiles

from ..core import loader
from ..core.log_helper import logger

_ALLOWED_FILES = frozenset({"config.json", "apis.json", "schedules.json", "groups.json", "auth.json"})

_PROJECT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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

    @app.get("/config")
    def get_config(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> Any:
        path = _path_for("config.json", data_dir)
        if not _ensure_inside(data_dir, path):
            raise HTTPException(status_code=400, detail="Invalid path")
        return _read_json(path, {})

    @app.put("/config")
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
        return {"status": "ok"}

    @app.get("/apis")
    def get_apis(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> list[Any]:
        return loader.load_apis(data_dir)

    @app.put("/apis")
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
        return {"status": "ok"}

    @app.get("/schedules")
    def get_schedules(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> list[Any]:
        return loader.load_schedules(data_dir)

    @app.put("/schedules")
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
        return {"status": "ok"}

    @app.get("/groups")
    def get_groups(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> Any:
        return loader.load_groups(data_dir)

    @app.put("/groups")
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
        return {"status": "ok"}

    @app.get("/auth")
    def get_auth(
        data_dir: Path = Depends(get_data_dir),
        _: None = Depends(require_password),
    ) -> Any:
        return loader.load_auth(data_dir)

    @app.put("/auth")
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
        return {"status": "ok"}

    dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if dist_dir.is_dir() and (dist_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

    return app


app = create_app()
