"""Keep configuration tests independent of the developer's shell and config."""

import os

import pytest

from sc2am.config_manager import ConfigManager


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    for name in os.environ:
        if name.startswith("SC2AM_"):
            monkeypatch.delenv(name)
    monkeypatch.setattr(ConfigManager, "CONFIG_DIR", tmp_path / ".sc2am")
    monkeypatch.setattr(ConfigManager, "CONFIG_FILE", tmp_path / ".sc2am" / "config.yaml")
