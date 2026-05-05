"""Foundation utilities: logger, palette, emojis, validators, safe decorator."""
from __future__ import annotations

import functools
import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

LOG_PATH = Path(__file__).resolve().parent.parent / "outputs" / "casa_ludic.log"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

PALETTE = {
    "primary": "#667eea",
    "secondary": "#764ba2",
    "success": "#4CAF50",
    "warn": "#FF9800",
    "error": "#F44336",
}

EMOJI = {
    "ok": "✓",
    "err": "✗",
    "warn": "⚠",
    "info": "\U0001f4cc",
    "hot": "\U0001f534",
    "warm": "\U0001f7e1",
    "cold": "⚪",
}

_PHONE_RE = re.compile(r"(\+?55\s?)?\(?(\d{2})\)?[\s-]?(\d{4,5})[\s-]?(\d{4})")
_EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

_LOGGER_CACHE: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Return a module logger that writes to outputs/casa_ludic.log."""
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.WARNING)
        logger.addHandler(sh)

    logger.propagate = False
    _LOGGER_CACHE[name] = logger
    return logger


F = TypeVar("F", bound=Callable[..., Any])


def safe(default: Any = False, log_name: str = "casa_ludic.safe") -> Callable[[F], F]:
    """Wrap a function so any exception is logged and `default` is returned (Padrao 3)."""
    log = get_logger(log_name)

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                log.error("%s falhou: %s", fn.__qualname__, exc, exc_info=True)
                return default
        return wrapper  # type: ignore[return-value]
    return decorator


def validate_phone(value: Optional[str]) -> Optional[str]:
    """Return digits-only BR phone (10-13 digits) or None if invalid."""
    if not value:
        return None
    match = _PHONE_RE.search(value)
    if not match:
        return None
    digits = "".join(d for d in match.group(0) if d.isdigit())
    if len(digits) < 10 or len(digits) > 13:
        return None
    return digits


def validate_email(value: Optional[str]) -> Optional[str]:
    """Return lowercased email or None if invalid."""
    if not value:
        return None
    candidate = value.strip().lower()
    return candidate if _EMAIL_RE.match(candidate) else None


_CONFIG_CACHE: Optional[dict[str, Any]] = None


def load_config() -> dict[str, Any]:
    """Load config.json once (cached)."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        try:
            with CONFIG_PATH.open(encoding="utf-8") as f:
                _CONFIG_CACHE = json.load(f)
        except Exception as exc:  # noqa: BLE001
            get_logger("casa_ludic.config").error("config.json invalido: %s", exc)
            _CONFIG_CACHE = {}
    return _CONFIG_CACHE


def emoji_for_priority(priority: str) -> str:
    return {"hot": EMOJI["hot"], "warm": EMOJI["warm"], "cold": EMOJI["cold"]}.get(priority, EMOJI["info"])
