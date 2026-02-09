# -*- coding: utf-8 -*-
"""Run config API: python -m api"""
import uvicorn
from . import app as application

if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", port=5787)
