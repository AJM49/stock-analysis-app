from __future__ import annotations

import logging


LOGGER_NAME = "stock_analysis_app"


def get_app_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def log_info(message: str) -> None:
    get_app_logger().info(message)


def log_warning(message: str) -> None:
    get_app_logger().warning(message)


def log_error(message: str, exc: Exception | None = None) -> None:
    logger = get_app_logger()
    if exc is None:
        logger.error(message)
    else:
        logger.exception("%s | error=%s", message, exc)
