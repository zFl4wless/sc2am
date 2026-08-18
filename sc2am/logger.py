"""
Logging configuration for sc2am.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """
    Set up logging with both console and optional file handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger("sc2am")
    requested_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(requested_level)
    logger.propagate = False

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler: keep CLI output clean by only surfacing warnings/errors.
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(max(requested_level, logging.WARNING))
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(requested_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
