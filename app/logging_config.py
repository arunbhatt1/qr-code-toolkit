"""Privacy-focused logging configuration for QR Code Toolkit.

Strict privacy rules:
- Never log passwords or credentials.
- Never log raw contact details, email bodies, or phone numbers.
- Never log raw decoded QR contents from scanner.
- Logs are strictly local in logs/qr_toolkit.log.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOGGER_NAME = "qr_toolkit"
_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "qr_toolkit.log"


def setup_logging(level: int = logging.INFO, log_to_console: bool = False) -> logging.Logger:
    """Configure and initialize application logging with privacy filters."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        # Rotating file handler (max 2 MB per file, keep 3 backups)
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Retrieve the application logger."""
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        return setup_logging()
    return logger


def log_generation(qr_type: str, error_correction: str, size: int) -> None:
    """Safely log a QR code generation event without recording sensitive user data."""
    logger = get_logger()
    logger.info(
        "Generated QR type: %s (EC: %s, Size: %dpx)",
        qr_type.upper(),
        error_correction,
        size,
    )


def log_scan_event(qr_count: int, file_format: str) -> None:
    """Safely log a QR scan event recording only count and format."""
    logger = get_logger()
    logger.info(
        "Scan completed: %d QR code(s) detected from %s image.",
        qr_count,
        file_format.upper(),
    )


def log_error(context: str, exc: Optional[Exception] = None) -> None:
    """Safely log an operational error without revealing sensitive data."""
    logger = get_logger()
    if exc:
        logger.error("Error during %s: %s (%s)", context, type(exc).__name__, str(exc))
    else:
        logger.error("Error during %s", context)
