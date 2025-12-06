"""
Logger utility for consistent logging across the application
"""
from pathlib import Path
import sys

from loguru import logger

from app.core.config import settings


def setup_logger(log_file: str = None, level: str = None, rotation: str = "10 MB") -> None:
    """
    Setup application logger with file and console output

    Args:
        log_file: Path to log file (defaults to settings.LOG_FILE)
        level: Log level (defaults to settings.LOG_LEVEL)
        rotation: Log rotation size (default: 10 MB)

    Example:
        setup_logger("logs/app.log", "DEBUG")
    """

    log_file = log_file or settings.LOG_FILE
    level = level or settings.LOG_LEVEL

    # Create log directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        level=level,
        colorize=True,
    )

    # File handler without colors
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation=rotation,
        retention="30 days",
        compression="zip",
    )

    logger.info(f"Logger initialized. File: {log_file}, Level: {level}")


def get_logger(name: str):
    """
    Get a logger instance for a specific module

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance

    Example:
    log = get_logger(__name__)
    log.info("Hello world")
    """

    return logger.bind(name=name)
