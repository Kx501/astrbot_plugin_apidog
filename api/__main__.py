# -*- coding: utf-8 -*-
"""Run config API: python -m api"""
from pathlib import Path

import uvicorn

from ..core.loader import get_api_port
from . import app as application

if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "data"
    port = get_api_port(data_dir)
    uvicorn.run(application, host="0.0.0.0", port=port)
