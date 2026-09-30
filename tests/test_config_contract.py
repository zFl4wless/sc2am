"""Configuration source precedence, normalization, and validation contract."""

from pathlib import Path

import pytest

from sc2am.config_manager import AppConfig, ConfigurationError, ConfigManager


@pytest.mark.parametrize(
    "contents",
    [
        "[]",
        "false",
        "0",
        "text",
        "- [log_level, DEBUG]",
        "1: value",
        "log_level: [",
        "typo_setting: true",
        "music_library_path: /tmp/music",
        "keep_downloads: false",
        "normalize_metadata: false",
        "skip_existing_tracks: true",
    ],
)
def test_invalid_config_is_never_silently_ignored(tmp_path, contents):
    path = tmp_path / "config.yaml"
    path.write_text(contents)
    with pytest.raises(ConfigurationError):
        ConfigManager.get_config(path)


@pytest.mark.parametrize("contents", ["", "# empty config", "null", "{}"])
def test_empty_config_uses_defaults(tmp_path, contents):
    path = tmp_path / "config.yaml"
    path.write_text(contents)
    assert ConfigManager.get_config(path) == AppConfig()


def test_custom_config_replaces_default_file(tmp_path):
    ConfigManager.CONFIG_FILE.parent.mkdir()
    ConfigManager.CONFIG_FILE.write_text("default_playlist: Default\nlog_level: ERROR\n")
    custom = tmp_path / "custom.yaml"
    custom.write_text("log_level: DEBUG\n")
    cfg = ConfigManager.get_config(custom)
    assert cfg.log_level == "DEBUG"
    assert cfg.default_playlist is None
    assert ConfigManager.get_config().default_playlist == "Default"


def test_explicit_missing_config_is_an_error(tmp_path):
    with pytest.raises(ConfigurationError, match="not found"):
        ConfigManager.get_config(tmp_path / "missing.yaml")
    assert ConfigManager.get_config() == AppConfig()


@pytest.mark.parametrize(
    "token,expected",
    [
        ("true", True),
        ("YES", True),
        ("1", True),
        (" on ", True),
        ("false", False),
        ("NO", False),
        ("0", False),
        (" off ", False),
    ],
)
@pytest.mark.parametrize("source", ["env", "yaml"])
def test_boolean_values_are_consistent(tmp_path, monkeypatch, token, expected, source):
    path = tmp_path / "config.yaml"
    if source == "env":
        path.write_text("")
        monkeypatch.setenv("SC2AM_CONTINUE_ON_ERROR", token)
    else:
        path.write_text(f'continue_on_error: "{token}"\n')
    assert ConfigManager.get_config(path).continue_on_error is expected


@pytest.mark.parametrize("token", ["", "tru", "maybe", "2"])
def test_invalid_env_boolean_is_rejected(monkeypatch, token):
    monkeypatch.setenv("SC2AM_OPEN_MUSIC", token)
    with pytest.raises(ConfigurationError, match="open_music_app"):
        ConfigManager.get_config()


@pytest.mark.parametrize(
    "field,env",
    [
        ("download_dir", "SC2AM_DOWNLOAD_DIR"),
        ("log_file", "SC2AM_LOG_FILE"),
    ],
)
def test_paths_expand_home_and_environment(tmp_path, monkeypatch, field, env):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SC2AM_TEST_FOLDER", "audio")
    monkeypatch.setenv(env, "~/$SC2AM_TEST_FOLDER")
    assert getattr(ConfigManager.get_config(), field) == tmp_path / "audio"


@pytest.mark.parametrize(
    "env,field",
    [
        ("SC2AM_PLAYLIST", "default_playlist"),
        ("SC2AM_LOG_FILE", "log_file"),
    ],
)
def test_empty_optional_values_clear_setting(monkeypatch, env, field):
    monkeypatch.setenv(env, "  ")
    assert getattr(ConfigManager.get_config(), field) is None


def test_empty_download_path_is_rejected(monkeypatch):
    monkeypatch.setenv("SC2AM_DOWNLOAD_DIR", "")
    with pytest.raises(ConfigurationError, match="download_dir"):
        ConfigManager.get_config()


def test_relative_paths_remain_relative_to_working_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("SC2AM_DOWNLOAD_DIR", "audio")
    assert ConfigManager.get_config().download_dir == Path("audio")


def test_unreadable_config_reports_path(tmp_path):
    with pytest.raises(ConfigurationError, match="Could not read configuration"):
        ConfigManager.get_config(tmp_path)


def test_invalid_encoding_is_reported(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ConfigurationError, match="Could not read configuration"):
        ConfigManager.get_config(path)
