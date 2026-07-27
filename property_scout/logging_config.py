"""Structured logging to console and a rotating file."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False


def setup_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger("property_scout")
    if _CONFIGURED:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "property_scout.log", maxBytes=2_000_000, backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        # File logging is best-effort; console always works.
        logger.warning("Could not open log file in %s; console only.", log_dir)

    logger.propagate = False
    _CONFIGURED = True
    return logger


def get_logger(name: str = "property_scout") -> logging.Logger:
    return logging.getLogger(name if name.startswith("property_scout") else f"property_scout.{name}")
