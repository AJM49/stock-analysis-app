from __future__ import annotations

import logging
from pathlib import Path


LOG_FILE = Path("app.log")


def get_app_logger(name: str = "stock_analysis_app") -> logging.Logger:
    """Return configured app logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)

    return logger


def log_error(error: Exception | str, context: str = "") -> None:
    """Log an error with optional context."""
    logger = get_app_logger()

    if isinstance(error, Exception):
        logger.exception("%s | %s", context, error)
    else:
        logger.error("%s | %s", context, error)


def log_info(message: str, context: str = "") -> None:
    """Log an info message."""
    logger = get_app_logger()

    if context:
        logger.info("%s | %s", context, message)
    else:
        logger.info(message)


def log_warning(message: str, context: str = "") -> None:
    """Log a warning message."""
    logger = get_app_logger()

    if context:
        logger.warning("%s | %s", context, message)
    else:
        logger.warning(message)


def log_app_error(error: Exception, context: str) -> None:
    """Backward-compatible app error logger."""
    log_error(error=error, context=context)


def log_app_info(message: str) -> None:
    """Backward-compatible app info logger."""
    log_info(message)
