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


@pytest.mark.parametrize("operation", ["open", "playlist"])
@pytest.mark.parametrize("failure", ["process_timeout", "appleevent_timeout", "busy", "denied"])
def test_import_failure_is_bounded_and_never_replayed(
    monkeypatch, tmp_path, sleep_mock, operation, failure
):
    track = tmp_path / "track.mp3"
    track.touch()
    monkeypatch.setattr(AppleMusicManager, "get_playlists", lambda: (True, ["Roadtrip"], ""))
    imported = []

    def run(command, **kwargs):
        if failure == "process_timeout":
            # Music can receive the event before its caller times out.
            imported.append(track)
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"partial")
        errors = {
            "appleevent_timeout": "Music got an error: AppleEvent timed out. (-1712)",
            "busy": "Application is busy; try again",
            "denied": "Not authorised to send Apple events. (-1743)",
        }
        return subprocess.CompletedProcess(command, 1, stdout="", stderr=errors[failure])

    run_mock = Mock(side_effect=run)
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)

    if operation == "open":
        success, message = AppleMusicManager.open_file_with_music(track)
        assert run_mock.call_args.args[0][:3] == ["open", "-a", "Music"]
    else:
        success, message = AppleMusicManager.add_to_playlist(track, "Roadtrip")
        assert run_mock.call_args.args[0][:2] == ["osascript", "-e"]

    assert success is False
    assert "This command was not retried" in message
    assert "Music may already have imported the track" in message
    assert "Check the Music library and target playlist before repeating" in message
    assert "avoid duplicates" in message
    if failure == "process_timeout":
        assert "timed out after 30 seconds" in message
        assert "check for permission prompts" in message
        assert imported == [track]
    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs == {
        "capture_output": True,
        "text": True,
        "timeout": 30,
    }
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
    assert "Check the Music library and target playlist" in result.output
    assert f"{expected_downloads} succeeded, 0 failed" in result.output
    assert downloader.download.call_count == expected_downloads
    assert run_mock.call_count == expected_downloads
    assert track.exists()
    sleep_mock.assert_not_called()
