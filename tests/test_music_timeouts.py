"""Bound Music commands without replaying an uncertain import."""

import subprocess
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

import main
import sc2am.apple_music as apple_music
from sc2am.apple_music import AppleMusicManager


@pytest.fixture
def sleep_mock(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(apple_music.time, "sleep", sleep)
    return sleep


@pytest.mark.parametrize("failure", ["process_timeout", "appleevent_timeout", "busy", "denied"])
def test_mutating_subprocess_is_bounded_and_never_replayed(monkeypatch, sleep_mock, failure):
    error = {
        "appleevent_timeout": "AppleEvent timed out",
        "busy": "Music is busy",
        "denied": "Not authorised (-1743)",
    }.get(failure)
    outcome = (
        subprocess.TimeoutExpired("osascript", 30)
        if failure == "process_timeout"
        else Mock(returncode=1, stdout="", stderr=error)
    )
    run_mock = (
        Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
    )
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)
    success, _, message = AppleMusicManager._run_osascript("test", "Importing into Music")
    assert not success
    assert "This command was not retried" in message
    assert "Music may already have imported the track" in message
    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["timeout"] == 30
    sleep_mock.assert_not_called()


@pytest.mark.parametrize("failure", ["process_timeout", "appleevent_timeout", "busy"])
def test_playlist_lookup_retries_safe_failures_then_succeeds(monkeypatch, sleep_mock, failure):
    first = (
        subprocess.TimeoutExpired("osascript", 30)
        if failure == "process_timeout"
        else Mock(
            returncode=1,
            stdout="",
            stderr="AppleEvent timed out" if failure == "appleevent_timeout" else "Music is busy",
        )
    )
    run_mock = Mock(side_effect=[first, Mock(returncode=0, stdout='["Roadtrip"]', stderr="")])
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)

    assert AppleMusicManager.get_playlists() == (True, ["Roadtrip"], "Playlists retrieved")
    assert run_mock.call_count == 2
    assert all(call.kwargs["timeout"] == 30 for call in run_mock.call_args_list)
    sleep_mock.assert_called_once_with(AppleMusicManager._RETRY_DELAY_SECONDS)


@pytest.mark.parametrize("operation", ["lookup", "playlist"])
def test_exhausted_lookup_timeouts_stop_without_import(
    monkeypatch, tmp_path, sleep_mock, operation
):
    track = tmp_path / "track.mp3"
    track.touch()
    run_mock = Mock(side_effect=subprocess.TimeoutExpired("osascript", 30))
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)

    if operation == "lookup":
        success, playlists, message = AppleMusicManager.get_playlists()
        assert playlists == []
    else:
        success, message = AppleMusicManager.add_to_playlist(track, "Roadtrip")

    assert success is False
    assert "Fetching playlists timed out after 30 seconds" in message
    assert "Open Music.app and check for permission prompts" in message
    assert "unexpected error" not in message
    assert run_mock.call_count == AppleMusicManager._MAX_RETRIES
    assert all(call.kwargs["timeout"] == 30 for call in run_mock.call_args_list)
    assert all("add sourcePath" not in call.args[0][2] for call in run_mock.call_args_list)
    assert [call.args[0] for call in sleep_mock.call_args_list] == [1.0, 2.0]


def test_permanent_lookup_failure_is_not_retried(monkeypatch, sleep_mock):
    run_mock = Mock(return_value=Mock(returncode=1, stdout="", stderr="Not authorised (-1743)"))
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)

    success, playlists, message = AppleMusicManager.get_playlists()

    assert (success, playlists) == (False, [])
    assert "Not authorised (-1743)" in message
    run_mock.assert_called_once()
    sleep_mock.assert_not_called()


def test_get_playlists_handles_missing_result_after_success(monkeypatch):
    monkeypatch.setattr(
        AppleMusicManager,
        "_run_osascript",
        lambda *args, **kwargs: (True, None, ""),
    )

    success, playlists, message = AppleMusicManager.get_playlists()

    assert (success, playlists) == (False, [])
    assert "Could not retrieve playlists" in message


@pytest.mark.parametrize("kind", ["single", "batch"])
@pytest.mark.parametrize("operation", ["open", "playlist"])
def test_cli_shows_timeout_warning_and_continues_downloads(
    monkeypatch, tmp_path, sleep_mock, kind, operation
):
    track = tmp_path / "track.mp3"
    track.touch()
    downloader = Mock()
    downloader.download.return_value = (True, track, "Downloaded")
    monkeypatch.setattr(main, "_create_downloader", Mock(return_value=downloader))
    monkeypatch.setattr(AppleMusicManager, "get_playlists", lambda: (True, ["Roadtrip"], ""))
    run_mock = Mock(side_effect=subprocess.TimeoutExpired("Music command", 30))
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)
    urls = ["https://soundcloud.com/artist/one", "https://soundcloud.com/artist/two"]
    if kind == "single":
        args = ["download", urls[0]]
        expected_downloads = 1
    else:
        batch = tmp_path / "urls.txt"
        batch.write_text("\n".join(urls), encoding="utf-8")
        args = ["batch", str(batch)]
        expected_downloads = 2
    args += (
        ["--open", "--playlist", ""]
        if operation == "open"
        else ["--no-open", "--playlist", "Roadtrip"]
    )

    result = CliRunner().invoke(main.cli, args)

    assert result.exit_code == 0, result.output
    assert "WARNING:" in result.output
    assert "timed out after 30 seconds" in result.output
    assert "Open Music.app and check for permission prompts" in result.output
    assert f"{expected_downloads} succeeded, 0 failed" in result.output
    assert downloader.download.call_count == expected_downloads
    assert run_mock.call_count == expected_downloads * AppleMusicManager._MAX_RETRIES
    assert track.exists()
    assert sleep_mock.call_count == expected_downloads * 2
