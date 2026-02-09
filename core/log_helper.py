# -*- coding: utf-8 -*-
"""Process-wide logger injection: framework entry sets it, packages use it; fallback to logging.getLogger(\"apidog\") when not set."""

from __future__ import annotations

import logging

_injected: logging.Logger | None = None


def set_apidog_logger(logger: logging.Logger | None) -> None:
    """Called by the bot framework entry on startup with the framework's logger."""
    global _injected
    _injected = logger


def get_apidog_logger() -> logging.Logger:
    """Return the injected logger if set, otherwise logging.getLogger('apidog')."""
    if _injected is not None:
        return _injected
    return logging.getLogger("apidog")


class _LoggerProxy:
    """Proxy: each attribute access forwards to the current logger from get_apidog_logger()."""

    def __getattr__(self, name: str):
        return getattr(get_apidog_logger(), name)


logger = _LoggerProxy()
