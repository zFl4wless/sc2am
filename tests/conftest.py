"""Keep configuration tests independent of the developer's shell and config."""

import logging
import os

import pytest

from sc2am.config_manager import ConfigManager


@pytest.fixture(autouse=True)
def isolated_logging():
    """Do not keep file handlers or Click's captured stderr across test runs."""
    logger = logging.getLogger("sc2am")
    old_handlers = logger.handlers[:]
    old_level, old_propagate = logger.level, logger.propagate
    logger.handlers = []
    yield
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logger.handlers = old_handlers
    logger.setLevel(old_level)
    logger.propagate = old_propagate


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    for name in os.environ:
        if name.startswith("SC2AM_"):
            monkeypatch.delenv(name)
    monkeypatch.setattr(ConfigManager, "CONFIG_DIR", tmp_path / ".sc2am")
    monkeypatch.setattr(ConfigManager, "CONFIG_FILE", tmp_path / ".sc2am" / "config.yaml")
