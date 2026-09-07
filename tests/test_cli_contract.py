"""Public command contract exercised through Click, with external work mocked."""

from unittest.mock import Mock

import pytest
import yaml
from click.testing import CliRunner

import main
from sc2am.config_manager import ConfigManager

URLS = ("https://soundcloud.com/artist/one", "https://soundcloud.com/artist/two")


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def backends(monkeypatch, tmp_path):
    downloader = Mock()
    downloader.download.return_value = (True, tmp_path / "track.mp3", "Downloaded")
    factory = Mock(return_value=downloader)
    music = Mock()
    music.open_file_with_music.return_value = (True, "Opened")
    music.add_to_playlist.return_value = (True, "Added")
    music_factory = Mock(return_value=music)
    monkeypatch.setattr(main, "_create_downloader", factory)
    monkeypatch.setattr(main, "AppleMusicManager", music_factory)
    return factory, downloader, music_factory, music


def command_args(kind, tmp_path, urls=URLS):
    if kind == "batch":
        batch = tmp_path / "urls.txt"
        batch.write_text("\n".join(urls), encoding="utf-8")
        return ["batch", str(batch)]
    return ["download", *(urls[:1] if kind == "single" else urls)]


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--help"],
        ["download", "--help"],
        ["batch", "--help"],
        ["config", "--help"],
        ["config", "init", "--help"],
        ["config", "show", "--help"],
    ],
)
def test_help_needs_no_configuration_or_backends(runner, monkeypatch, backends, args):
    monkeypatch.setenv("SC2AM_LOG_LEVEL", "invalid")
    result = runner.invoke(main.cli, args)
    assert result.exit_code == (2 if not args else 0), result.output
    assert "Usage:" in result.output
    backends[0].assert_not_called()
    backends[2].assert_not_called()


@pytest.mark.parametrize(
    "env,cli,expected",
    [(None, [], "WARNING"), ("error", [], "ERROR"), ("invalid", ["--log-level", "debug"], "DEBUG")],
)
def test_effective_log_level_precedence(runner, tmp_path, monkeypatch, env, cli, expected):
    config = tmp_path / "config.yaml"
    config.write_text("log_level: warning\ncontinue_on_error: true\n")
    if env is not None:
        monkeypatch.setenv("SC2AM_LOG_LEVEL", env)
    result = runner.invoke(main.cli, ["--config", str(config), *cli, "config", "show"])
    assert result.exit_code == 0, result.output
    assert f"Log Level:           {expected}" in result.output
    assert "Continue on Error:   True" in result.output


@pytest.mark.parametrize("kind", ["single", "multiple", "batch"])
def test_dry_run_does_not_initialize_backends_or_write_files(
    runner, tmp_path, monkeypatch, backends, kind
):
    downloads = tmp_path / "downloads"
    log_file = tmp_path / "logs" / "sc2am.log"
    monkeypatch.setenv("SC2AM_DOWNLOAD_DIR", str(downloads))
    monkeypatch.setenv("SC2AM_LOG_FILE", str(log_file))
    monkeypatch.setenv("SC2AM_PLAYLIST", "Roadtrip")
    result = runner.invoke(main.cli, [*command_args(kind, tmp_path), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Would download track" in result.output
    assert "Would open with Apple Music" in result.output
    assert "Would add to playlist 'Roadtrip'" in result.output
    backends[0].assert_not_called()
    backends[2].assert_not_called()
    assert not downloads.exists()
    assert not log_file.parent.exists()
    assert not ConfigManager.CONFIG_FILE.exists()


@pytest.mark.parametrize("kind", ["single", "multiple", "batch"])
@pytest.mark.parametrize(
    "value,flags,should_open",
    [
        ("true", ["--no-open"], False),
        ("false", ["--open"], True),
        ("false", [], False),
        ("true", [], True),
    ],
)
def test_open_flag_overrides_configuration(
    runner, tmp_path, monkeypatch, backends, kind, value, flags, should_open
):
    monkeypatch.setenv("SC2AM_OPEN_MUSIC", value)
    result = runner.invoke(main.cli, [*command_args(kind, tmp_path), *flags])
    assert result.exit_code == 0, result.output
    assert backends[3].open_file_with_music.called == should_open


@pytest.mark.parametrize("kind", ["single", "multiple", "batch"])
@pytest.mark.parametrize(
    "flags,expected",
    [([], "Default"), (["--playlist", "  Custom  "], "Custom"), (["--playlist", ""], None)],
)
def test_playlist_override_and_disable(
    runner, tmp_path, monkeypatch, backends, kind, flags, expected
):
    monkeypatch.setenv("SC2AM_PLAYLIST", "Default")
    result = runner.invoke(main.cli, [*command_args(kind, tmp_path), "--no-open", *flags])
    assert result.exit_code == 0, result.output
    backends[3].open_file_with_music.assert_not_called()
    calls = backends[3].add_to_playlist.call_args_list
    assert bool(calls) == (expected is not None)
    assert all(call.args[1] == expected for call in calls)


@pytest.mark.parametrize("kind", ["multiple", "batch"])
@pytest.mark.parametrize(
    "env,flags,count",
    [
        ("true", [], 2),
        ("true", ["--stop-on-error"], 1),
        ("false", [], 1),
        ("false", ["--continue-on-error"], 2),
    ],
)
def test_continue_flag_precedence(runner, tmp_path, monkeypatch, backends, kind, env, flags, count):
    monkeypatch.setenv("SC2AM_CONTINUE_ON_ERROR", env)
    backends[1].download.side_effect = [
        (False, None, "Track missing"),
        (True, tmp_path / "ok.mp3", "Downloaded"),
    ]
    result = runner.invoke(main.cli, [*command_args(kind, tmp_path), "--no-open", *flags])
    assert result.exit_code == 1, result.output
    assert backends[1].download.call_count == count
    assert "1 failed" in result.output


@pytest.mark.parametrize("kind", ["single", "multiple", "batch"])
def test_missing_download_file_is_counted_as_failure(runner, tmp_path, backends, kind):
    backends[1].download.return_value = (True, None, "Downloaded")
    result = runner.invoke(main.cli, [*command_args(kind, tmp_path), "--continue-on-error"])
    count = 1 if kind == "single" else 2
    assert result.exit_code == 1, result.output
    assert f"0 succeeded, {count} failed" in result.output
    assert "MP3 file could not be located" in result.output
    backends[2].assert_not_called()


@pytest.mark.parametrize("kind", ["single", "multiple", "batch"])
def test_invalid_input_stops_before_backend_setup(runner, tmp_path, backends, kind):
    result = runner.invoke(main.cli, command_args(kind, tmp_path, ("invalid", *URLS)))
    assert result.exit_code == 2, result.output
    backends[0].assert_not_called()
    backends[2].assert_not_called()


@pytest.mark.parametrize("kind", ["multiple", "batch"])
def test_skipped_invalid_input_still_fails_run(runner, tmp_path, backends, kind):
    result = runner.invoke(
        main.cli,
        [*command_args(kind, tmp_path, ("invalid", *URLS)), "--continue-on-error", "--no-open"],
    )
    assert result.exit_code == 1, result.output
    assert backends[1].download.call_count == 2
    assert "2 succeeded, 1 failed" in result.output


@pytest.mark.parametrize(
    "args",
    [
        ["download"],
        ["unknown"],
        ["--log-level", "invalid", "config", "show"],
        ["download", URLS[0], "--log-level", "DEBUG"],
    ],
)
def test_invalid_cli_usage_returns_two(runner, backends, args):
    result = runner.invoke(main.cli, args)
    assert result.exit_code == 2, result.output
    backends[0].assert_not_called()


def test_batch_rejects_directory_and_empty_file(runner, tmp_path, backends):
    for path in (tmp_path, tmp_path / "empty.txt"):
        if path != tmp_path:
            path.write_text("# Comment\n\n")
        result = runner.invoke(main.cli, ["batch", str(path)])
        assert result.exit_code == 2, result.output
    backends[0].assert_not_called()


@pytest.mark.parametrize("custom", [False, True])
def test_init_preserves_and_repairs_invalid_config(runner, tmp_path, monkeypatch, custom):
    target = tmp_path / "custom.yaml" if custom else ConfigManager.CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("invalid: [")
    prefix = ["--config", str(target)] if custom else []
    monkeypatch.setenv("SC2AM_KEEP_DOWNLOADS", "typo")
    result = runner.invoke(main.cli, [*prefix, "config", "init"])
    assert result.exit_code == 0, result.output
    assert "already exists" in result.output
    assert target.read_text() == "invalid: ["
    result = runner.invoke(main.cli, [*prefix, "config", "init", "--force"])
    assert result.exit_code == 0, result.output
    assert yaml.safe_load(target.read_text()) == ConfigManager.default_config_data()


def test_init_can_create_custom_path(runner, tmp_path):
    target = tmp_path / "nested" / "custom.yaml"
    result = runner.invoke(main.cli, ["--config", str(target), "config", "init"])
    assert result.exit_code == 0, result.output
    assert target.exists()
    assert not ConfigManager.CONFIG_FILE.exists()


def test_config_errors_are_actionable(runner, monkeypatch):
    monkeypatch.setenv("SC2AM_KEEP_DOWNLOADS", "typo")
    result = runner.invoke(main.cli, ["config", "show"])
    assert result.exit_code == 2, result.output
    assert "keep_downloads" in result.output
    assert "true/false" in result.output
    assert "Traceback" not in result.output


def test_show_does_not_create_log_file(runner, tmp_path, monkeypatch):
    target = tmp_path / "logs" / "sc2am.log"
    monkeypatch.setenv("SC2AM_LOG_FILE", str(target))
    assert runner.invoke(main.cli, ["config", "show"]).exit_code == 0
    assert not target.parent.exists()


def test_log_file_error_is_readable(runner, tmp_path, monkeypatch, backends):
    monkeypatch.setenv("SC2AM_LOG_FILE", str(tmp_path))
    result = runner.invoke(main.cli, ["download", URLS[0]])
    assert result.exit_code == 1, result.output
    assert "Could not open log file" in result.output
    backends[0].assert_not_called()


def test_music_warnings_preserve_download_success(runner, backends):
    backends[3].open_file_with_music.return_value = (False, "Music unavailable")
    backends[3].add_to_playlist.return_value = (False, "Playlist missing")
    result = runner.invoke(main.cli, ["download", URLS[0], "--playlist", "Example"])
    assert result.exit_code == 0, result.output
    assert "WARNING: Music unavailable" in result.output
    assert "WARNING: Playlist missing" in result.output
    assert "1 succeeded, 0 failed" in result.output


@pytest.mark.parametrize("kind", ["single", "multiple", "batch"])
def test_explicit_options_replace_invalid_lower_priority_values(
    runner, tmp_path, monkeypatch, backends, kind
):
    monkeypatch.setenv("SC2AM_OPEN_MUSIC", "typo")
    monkeypatch.setenv("SC2AM_CONTINUE_ON_ERROR", "typo")
    result = runner.invoke(
        main.cli, [*command_args(kind, tmp_path), "--no-open", "--stop-on-error"]
    )
    assert result.exit_code == 0, result.output
    backends[2].assert_not_called()


def test_unreadable_batch_never_processes_partial_results(runner, tmp_path, monkeypatch, backends):
    path = tmp_path / "urls.txt"
    path.write_text(URLS[0])
    monkeypatch.setattr(
        main.URLValidator,
        "validate_batch_file",
        lambda _: (False, [URLS[0]], [(0, "Could not read file")]),
    )
    result = runner.invoke(main.cli, ["batch", str(path), "--continue-on-error"])
    assert result.exit_code == 2, result.output
    assert "UTF-8 encoding" in result.output
    backends[0].assert_not_called()


def test_missing_download_dependency_counts_failure(runner, monkeypatch, backends):
    def unavailable(*args):
        raise main.click.ClickException("Unable to prepare downloads.")

    monkeypatch.setattr(main, "_create_downloader", unavailable)
    result = runner.invoke(main.cli, ["download", URLS[0]])
    assert result.exit_code == 1, result.output
    assert "Unable to prepare downloads" in result.output
    assert "0 succeeded, 1 failed" in result.output
    backends[2].assert_not_called()
