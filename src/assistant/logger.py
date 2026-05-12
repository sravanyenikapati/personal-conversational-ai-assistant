"""
Structured logging setup using Rich.

Usage anywhere in the project:
    from assistant.logger import get_logger
    log = get_logger(__name__)
    log.info("Assistant started")
    log.error("Something went wrong", exc_info=True)
"""

import logging
import sys

from rich.logging import RichHandler


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with Rich formatting."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = RichHandler(
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_time=True,
            show_path=True,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
        logger.addHandler(handler)
        logger.propagate = False

    return logger


def configure_root_logger(level: str = "INFO") -> None:
    """Configure the root logger level for the whole app. Call once at startup."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_time=True,
                markup=True,
                stream=sys.stdout,
            )
        ],
        format="%(message)s",
        datefmt="[%X]",
    )
    # Silence noisy third-party loggers
    for noisy in ("httpcore", "httpx", "openai", "anthropic", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
