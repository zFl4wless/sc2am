"""Exercise diagnostics through the CLI with real logging and mocked processes."""

import subprocess
from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

import main
import sc2am.downloader as downloader_module
from sc2am.apple_music import AppleMusicManager
from sc2am.downloader import Downloader

URL = "https://soundcloud.com/artist/track"


def diagnostic_args(command, tmp_path):
    if command == "batch":
        path = tmp_path / "urls.txt"
        path.write_text(URL + "\n", encoding="utf-8")
        return ["batch", str(path)]
    return ["download", URL]


@pytest.mark.parametrize("command", ["download", "batch"])
@pytest.mark.parametrize("stage", ["track-info", "download"])
@pytest.mark.parametrize("logging_mode", ["default", "debug-console", "info-file"])
def test_process_failures_have_usable_diagnostics(
    monkeypatch, tmp_path, command, stage, logging_mode
):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    monkeypatch.setenv("SC2AM_DOWNLOAD_DIR", str(tmp_path / "downloads"))
    if stage == "download":
        monkeypatch.setattr(
            Downloader, "get_track_info", staticmethod(lambda _: (True, {"id": "123"}, "OK"))
        )
    cause = "ERROR: extractor failed with diagnostic cause 123"
    monkeypatch.setattr(
        downloader_module.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 1, "", cause)),
    )
    log_file = tmp_path / "logs" / "sc2am.log"
    if logging_mode == "info-file":
        monkeypatch.setenv("SC2AM_LOG_FILE", str(log_file))
    prefix = ["--log-level", "DEBUG"] if logging_mode == "debug-console" else []
    result = CliRunner().invoke(
        main.cli, [*prefix, *diagnostic_args(command, tmp_path), "--no-open", "--playlist", ""]
    )

    assert result.exit_code == 1, result.output
    assert "sc2am --log-level DEBUG download URL" in result.output
    assert "sc2am --log-level DEBUG batch FILE" in result.output
    assert "check the log file" not in result.output.lower()
    assert "0 succeeded, 1 failed" in result.output
    if logging_mode == "debug-console":
        assert "DEBUG: Running" in result.stderr
        assert "yt-dlp --ignore-config" in result.stderr
    else:
        assert "DEBUG:" not in result.stderr
        assert "INFO:" not in result.stderr
    if logging_mode == "info-file":
        contents = log_file.read_text()
        assert cause in contents
        assert f"yt-dlp {stage} exited with 1" in contents
    else:
        assert not log_file.exists()


@pytest.mark.parametrize("stage", ["track-info", "download"])
def test_configured_debug_file_retains_exception_and_command(monkeypatch, tmp_path, stage):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    monkeypatch.setenv("SC2AM_DOWNLOAD_DIR", str(tmp_path / "downloads"))
    monkeypatch.setenv("SC2AM_LOG_FILE", str(tmp_path / "sc2am.log"))
    if stage == "download":
        monkeypatch.setattr(
            Downloader, "get_track_info", staticmethod(lambda _: (True, {"id": "123"}, "OK"))
        )
    monkeypatch.setattr(
        downloader_module.subprocess, "run", Mock(side_effect=OSError("process could not start"))
    )
    result = CliRunner().invoke(main.cli, ["--log-level", "DEBUG", "download", URL])

    assert result.exit_code == 1, result.output
    assert "sc2am --log-level DEBUG" in result.output
    contents = (tmp_path / "sc2am.log").read_text()
    assert "Traceback" in contents
    assert "OSError: process could not start" in contents
    assert "yt-dlp --ignore-config" in contents


def test_missing_dependency_includes_install_command_without_log_file(monkeypatch):
    monkeypatch.setattr(downloader_module.shutil, "which", lambda _: None)
    result = CliRunner().invoke(main.cli, ["download", URL])

    assert result.exit_code == 1, result.output
    assert "Unable to prepare downloads. yt-dlp is not installed" in result.output
    assert "pip install yt-dlp" in result.output
    assert "0 succeeded, 1 failed" in result.output


def test_invalid_track_info_retains_parse_cause_in_log(monkeypatch, tmp_path):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    monkeypatch.setattr(downloader_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        downloader_module.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 0, "not JSON", "")),
    )
    monkeypatch.setenv("SC2AM_LOG_FILE", str(tmp_path / "sc2am.log"))
    result = CliRunner().invoke(main.cli, ["download", URL])

    assert result.exit_code == 1, result.output
    assert "Could not read track information" in result.output
    assert "sc2am --log-level DEBUG" in result.output
    assert "JSONDecodeError" in (tmp_path / "sc2am.log").read_text()


@pytest.mark.parametrize("operation", ["open", "list", "add"])
@pytest.mark.parametrize("file_logging", [False, True])
def test_unexpected_music_errors_offer_remedies_and_retain_causes(
    monkeypatch, tmp_path, operation, file_logging
):
    track = tmp_path / "track.mp3"
    track.touch()
    downloader = Mock()
    downloader.download.return_value = (True, track, "Downloaded")
    monkeypatch.setattr(main, "_create_downloader", lambda *_: downloader)
    run = Mock(side_effect=OSError("Music diagnostic cause"))
    if operation == "open":
        monkeypatch.setattr(AppleMusicManager, "_run_command_with_retry", run)
        options = []
    else:
        monkeypatch.setattr(AppleMusicManager, "_run_osascript", run)
        options = ["--no-open", "--playlist", "Roadtrip"]
        if operation == "add":
            monkeypatch.setattr(
                AppleMusicManager, "get_playlists", lambda: (True, ["Roadtrip"], "OK")
            )
    log_file = tmp_path / "sc2am.log"
    if file_logging:
        monkeypatch.setenv("SC2AM_LOG_FILE", str(log_file))
    result = CliRunner().invoke(main.cli, ["download", URL, *options])

    assert result.exit_code == 0, result.output
    assert "WARNING: Could not" in result.output
    assert "Music.app" in result.output
    assert "sc2am --log-level DEBUG download URL" in result.output
    assert "check the log file" not in result.output.lower()
    if file_logging:
        contents = log_file.read_text()
        assert "Traceback" in contents
        assert "OSError: Music diagnostic cause" in contents


@pytest.mark.parametrize("file_logging", [False, True])
def test_unhandled_cli_error_gives_diagnostic_command(monkeypatch, tmp_path, file_logging):
    if file_logging:
        monkeypatch.setenv("SC2AM_LOG_FILE", str(tmp_path / "sc2am.log"))
    original_cli = main.cli
    monkeypatch.setattr(main, "cli", lambda **_: original_cli.main(args=["download", URL]))
    monkeypatch.setattr(main, "_run_tracks", Mock(side_effect=RuntimeError("CLI diagnostic cause")))
    result = CliRunner().invoke(click.Command("entry", callback=main.main))

    assert result.exit_code == 1, result.output
    assert "An unexpected error occurred" in result.stderr
    assert "sc2am --log-level DEBUG download URL" in result.stderr
    assert "check the log file" not in result.output.lower()
    if file_logging:
        contents = (tmp_path / "sc2am.log").read_text()
        assert "Traceback" in contents
        assert "RuntimeError: CLI diagnostic cause" in contents
