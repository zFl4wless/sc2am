"""Tests for the external boundaries in SC2AM's download and Music workflows."""

import json
import os
import subprocess
from unittest.mock import Mock

import pytest

import sc2am.apple_music as apple_music
import sc2am.downloader as downloader_module
from sc2am.apple_music import AppleMusicManager
from sc2am.downloader import Downloader


@pytest.fixture
def downloader(tmp_path, monkeypatch):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    return Downloader(tmp_path / "downloads")


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        (
            "ERROR: Unsupported URL",
            "The URL is invalid or not supported. Please check the link and try again.",
        ),
        (
            "HTTP Error 403: Forbidden",
            "The track is private or unavailable. Please use a public SoundCloud track URL.",
        ),
        (
            "Connection reset by peer",
            "A temporary network error occurred. Please try again.",
        ),
        (
            "an unrecognised failure",
            "The download failed unexpectedly. Please check the log file for details.",
        ),
    ],
)
def test_downloader_classifies_all_user_facing_error_categories(stderr, expected):
    assert Downloader._classify_download_error(stderr) == expected


def test_downloader_rejects_missing_yt_dlp(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader_module.shutil, "which", lambda _: None)

    with pytest.raises(RuntimeError, match="yt-dlp is not installed"):
        Downloader(tmp_path)


def test_downloader_embeds_available_metadata_and_uses_yt_dlp_output(
    downloader, tmp_path, monkeypatch
):
    track_path = tmp_path / "downloads" / "night-drive.mp3"
    track_path.parent.mkdir()
    track_path.touch()
    track_info = {"title": "Night Drive", "artist": "Synthwave Collective"}
    downloader.metadata_writer = Mock()
    downloader.metadata_writer.write_to_file.return_value = (True, "Metadata embedded")
    monkeypatch.setattr(
        downloader,
        "get_track_info",
        lambda _: (True, track_info, "Info fetched successfully"),
    )
    run_mock = Mock(return_value=Mock(returncode=0, stdout=json.dumps(str(track_path)), stderr=""))
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)

    success, result_path, message = downloader.download("https://soundcloud.com/artist/night-drive")

    assert success is True
    assert result_path == track_path
    assert message == "Downloaded: night-drive.mp3 (metadata embedded)"
    downloader.metadata_writer.write_to_file.assert_called_once_with(track_path, track_info)
    command = run_mock.call_args.args[0]
    assert command[:2] == ["yt-dlp", "--format"]
    assert "after_move:%(filepath)j" in command
    assert command[-1] == "https://soundcloud.com/artist/night-drive"


def test_downloader_keeps_download_when_metadata_tagging_fails(downloader, tmp_path, monkeypatch):
    track_path = tmp_path / "downloads" / "untagged.mp3"
    track_path.parent.mkdir()
    track_path.touch()
    downloader.metadata_writer = Mock()
    downloader.metadata_writer.write_to_file.return_value = (False, "Invalid ID3 frame")
    monkeypatch.setattr(
        downloader,
        "get_track_info",
        lambda _: (True, {"title": "Untitled"}, "Info fetched successfully"),
    )
    monkeypatch.setattr(
        downloader_module.subprocess,
        "run",
        lambda *args, **kwargs: Mock(returncode=0, stdout=json.dumps(str(track_path)), stderr=""),
    )

    success, result_path, message = downloader.download("https://soundcloud.com/artist/untagged")

    assert success is True
    assert result_path == track_path
    assert message == "Downloaded: untagged.mp3 (metadata could not be added)"


def test_downloader_retries_when_yt_dlp_reports_success_without_an_mp3(downloader, monkeypatch):
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (False, None, "Unavailable"))
    monkeypatch.setattr(downloader, "_resolve_downloaded_file", lambda _: None)
    run_mock = Mock(return_value=Mock(returncode=0, stdout="", stderr=""))
    sleep_mock = Mock()
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)
    monkeypatch.setattr(downloader_module.time, "sleep", sleep_mock)

    success, result_path, message = downloader.download("https://soundcloud.com/artist/missing")

    assert (success, result_path, message) == (
        False,
        None,
        "The downloaded MP3 file could not be verified. Please try again.",
    )
    assert run_mock.call_count == Downloader._MAX_RETRIES
    assert sleep_mock.call_count == Downloader._MAX_RETRIES - 1


def test_downloader_retries_timeout_then_returns_actionable_error(downloader, monkeypatch):
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (False, None, "Unavailable"))
    run_mock = Mock(side_effect=subprocess.TimeoutExpired("yt-dlp", 300))
    sleep_mock = Mock()
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)
    monkeypatch.setattr(downloader_module.time, "sleep", sleep_mock)

    success, result_path, message = downloader.download("https://soundcloud.com/artist/slow")

    assert (success, result_path, message) == (
        False,
        None,
        "The download timed out. Please try again later.",
    )
    assert run_mock.call_count == Downloader._MAX_RETRIES
    assert sleep_mock.call_count == Downloader._MAX_RETRIES - 1


def test_downloader_retries_temporary_failure_then_succeeds(downloader, tmp_path, monkeypatch):
    track_path = tmp_path / "downloads" / "retry.mp3"
    track_path.parent.mkdir()
    track_path.touch()
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (False, None, "Unavailable"))
    run_mock = Mock(
        side_effect=[
            Mock(returncode=1, stdout="", stderr="HTTP Error 503: Service Unavailable"),
            Mock(returncode=0, stdout=json.dumps(str(track_path)), stderr=""),
        ]
    )
    sleep_mock = Mock()
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)
    monkeypatch.setattr(downloader_module.time, "sleep", sleep_mock)

    success, result_path, message = downloader.download("https://soundcloud.com/artist/retry")

    assert (success, result_path, message) == (
        True,
        track_path,
        "Downloaded: retry.mp3",
    )
    assert run_mock.call_count == 2
    sleep_mock.assert_called_once_with(Downloader._RETRY_DELAY_SECONDS)


def test_downloader_surfaces_unexpected_process_failure(downloader, monkeypatch):
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (False, None, "Unavailable"))
    monkeypatch.setattr(
        downloader_module.subprocess,
        "run",
        Mock(side_effect=OSError("yt-dlp unavailable")),
    )

    success, result_path, message = downloader.download("https://soundcloud.com/artist/unexpected")

    assert (success, result_path, message) == (
        False,
        None,
        "The download failed unexpectedly. Please check the log file for details.",
    )


@pytest.mark.parametrize(
    "output_kind",
    [
        "empty",
        "malformed",
        "missing",
        "directory",
        "non-mp3",
        "outside",
        "symlink",
        "relative",
        "multiple",
        "null",
        "object",
        "blank",
    ],
)
def test_unverified_download_never_tags_or_imports_existing_files(
    downloader, tmp_path, monkeypatch, output_kind
):
    from click.testing import CliRunner
    import main

    downloader.download_dir.mkdir()
    stale = downloader.download_dir / "stale.mp3"
    stale.write_bytes(b"existing recording")
    directory = downloader.download_dir / "directory.mp3"
    directory.mkdir()
    non_mp3 = downloader.download_dir / "track.wav"
    non_mp3.touch()
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"other recording")
    symlink = downloader.download_dir / "link.mp3"
    symlink.symlink_to(stale)
    outputs = {
        "empty": "",
        "malformed": "not a path",
        "missing": json.dumps(str(downloader.download_dir / "missing.mp3")),
        "directory": json.dumps(str(directory)),
        "non-mp3": json.dumps(str(non_mp3)),
        "outside": json.dumps(str(outside)),
        "symlink": json.dumps(str(symlink)),
        "relative": json.dumps("stale.mp3"),
        "multiple": json.dumps(str(stale)) + "\n" + json.dumps(str(stale)),
        "null": "null",
        "object": "{}",
        "blank": '""',
    }
    downloader.metadata_writer = Mock()
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (True, {"title": "New"}, "OK"))
    monkeypatch.setattr(downloader_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        downloader_module.subprocess,
        "run",
        Mock(return_value=Mock(returncode=0, stdout=outputs[output_kind], stderr="")),
    )
    monkeypatch.setattr(main, "_create_downloader", lambda *args: downloader)
    music_factory = Mock()
    monkeypatch.setattr(main, "AppleMusicManager", music_factory)

    result = CliRunner().invoke(
        main.cli, ["download", "https://soundcloud.com/artist/new", "--playlist", "Roadtrip"]
    )

    assert result.exit_code == 1, result.output
    assert "The downloaded MP3 file could not be verified. Please try again." in result.output
    assert "0 succeeded, 1 failed" in result.output
    downloader.metadata_writer.write_to_file.assert_not_called()
    music_factory.assert_not_called()
    assert stale.read_bytes() == b"existing recording"
    assert outside.read_bytes() == b"other recording"


@pytest.mark.parametrize("has_output", [False, True])
def test_overlapping_downloads_only_tag_their_own_reported_file(
    downloader, monkeypatch, has_output
):
    downloader.download_dir.mkdir()
    own_path = downloader.download_dir / "own.mp3"
    own_path.write_bytes(b"own recording")
    other_path = downloader.download_dir / "other.mp3"
    other = Downloader(downloader.download_dir)
    own_info, other_info = {"title": "Own"}, {"title": "Other"}
    for instance, info in ((downloader, own_info), (other, other_info)):
        instance.metadata_writer = Mock()
        instance.metadata_writer.write_to_file.return_value = (True, "OK")
        monkeypatch.setattr(instance, "get_track_info", lambda _, info=info: (True, info, "OK"))
    monkeypatch.setattr(downloader, "_MAX_RETRIES", 1)

    def run(command, **kwargs):
        if command[-1].endswith("/own"):
            # Complete the overlapping run while this download is still in progress.
            assert other.download("https://soundcloud.com/artist/other")[0]
            output = json.dumps(str(own_path)) if has_output else ""
        else:
            other_path.write_bytes(b"other recording")
            os.utime(own_path, (1, 1))
            output = json.dumps(str(other_path))
        return Mock(returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(downloader_module.subprocess, "run", run)
    success, path, _ = downloader.download("https://soundcloud.com/artist/own")

    assert success is has_output
    assert path == (own_path if has_output else None)
    if has_output:
        downloader.metadata_writer.write_to_file.assert_called_once_with(own_path, own_info)
    else:
        downloader.metadata_writer.write_to_file.assert_not_called()
    other.metadata_writer.write_to_file.assert_called_once_with(other_path, other_info)
    assert own_path.read_bytes() == b"own recording"


def test_reported_path_preserves_whitespace_and_unicode(downloader):
    downloader.download_dir.mkdir()
    path = downloader.download_dir / '  Nacht "mix"\n音楽.mp3'
    path.touch()
    assert downloader._resolve_downloaded_file(json.dumps(str(path)) + "\n") == path


def test_track_info_retries_invalid_json_and_returns_parsed_metadata(monkeypatch):
    valid_info = {"title": "Night Drive"}
    run_mock = Mock(
        side_effect=[
            Mock(returncode=0, stdout="not json", stderr=""),
            Mock(returncode=0, stdout=json.dumps(valid_info), stderr=""),
        ]
    )
    sleep_mock = Mock()
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)
    monkeypatch.setattr(downloader_module.time, "sleep", sleep_mock)

    success, info, message = Downloader.get_track_info("https://soundcloud.com/artist/night-drive")

    assert (success, info, message) == (True, valid_info, "Info fetched successfully")
    assert run_mock.call_count == 2
    sleep_mock.assert_called_once_with(Downloader._RETRY_DELAY_SECONDS)


def test_track_info_returns_classified_permanent_failure_without_retry(monkeypatch):
    run_mock = Mock(return_value=Mock(returncode=1, stdout="", stderr="HTTP Error 404: Not Found"))
    sleep_mock = Mock()
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)
    monkeypatch.setattr(downloader_module.time, "sleep", sleep_mock)

    success, info, message = Downloader.get_track_info("https://soundcloud.com/artist/missing")

    assert (success, info) == (False, None)
    assert message.startswith("Could not fetch track info: The track could not be found")
    run_mock.assert_called_once()
    sleep_mock.assert_not_called()


def test_opening_non_mp3_never_invokes_music(monkeypatch, tmp_path):
    file_path = tmp_path / "track.wav"
    file_path.touch()
    run_mock = Mock()
    monkeypatch.setattr(AppleMusicManager, "_run_command_with_retry", run_mock)

    success, message = AppleMusicManager.open_file_with_music(file_path)

    assert (success, message) == (False, "The selected file is not an MP3.")
    run_mock.assert_not_called()


def test_opening_missing_file_never_invokes_music(monkeypatch, tmp_path):
    run_mock = Mock()
    monkeypatch.setattr(AppleMusicManager, "_run_command_with_retry", run_mock)

    success, message = AppleMusicManager.open_file_with_music(tmp_path / "missing.mp3")

    assert (success, message) == (False, "The downloaded file was not found.")
    run_mock.assert_not_called()


def test_music_command_does_not_retry_permanent_error(monkeypatch):
    result = Mock(returncode=1, stdout="", stderr="Application not found")
    run_mock = Mock(return_value=result)
    sleep_mock = Mock()
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)
    monkeypatch.setattr(apple_music.time, "sleep", sleep_mock)

    success, returned_result, error = AppleMusicManager._run_command_with_retry(
        ["open", "-a", "Music", "track.mp3"], "Opening file with Music"
    )

    assert (success, returned_result, error) == (False, result, "Application not found")
    run_mock.assert_called_once()
    sleep_mock.assert_not_called()


def test_music_command_retries_temporary_error_then_succeeds(monkeypatch):
    results = [
        Mock(returncode=1, stdout="", stderr="Application isn't responding"),
        Mock(returncode=0, stdout="", stderr=""),
    ]
    run_mock = Mock(side_effect=results)
    sleep_mock = Mock()
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)
    monkeypatch.setattr(apple_music.time, "sleep", sleep_mock)

    success, returned_result, error = AppleMusicManager._run_command_with_retry(
        ["open", "-a", "Music", "track.mp3"], "Opening file with Music"
    )

    assert (success, returned_result, error) == (True, results[1], "")
    assert run_mock.call_count == 2
    sleep_mock.assert_called_once_with(AppleMusicManager._RETRY_DELAY_SECONDS)


def test_get_playlists_parses_osascript_output(monkeypatch):
    result = Mock(stdout="Library, Roadtrip,  Focus  ,\n")
    monkeypatch.setattr(AppleMusicManager, "_run_osascript", lambda *args: (True, result, ""))

    success, playlists, message = AppleMusicManager.get_playlists()

    assert (success, playlists, message) == (
        True,
        ["Library", "Roadtrip", "Focus"],
        "Playlists retrieved",
    )


def test_get_playlists_surfaces_automation_failure(monkeypatch):
    monkeypatch.setattr(
        AppleMusicManager,
        "_run_osascript",
        lambda *args: (False, Mock(), "Not authorised"),
    )

    success, playlists, message = AppleMusicManager.get_playlists()

    assert (success, playlists) == (False, [])
    assert "Not authorised" in message
    assert "Automation permissions" in message


def test_add_to_playlist_stops_when_playlist_name_is_blank(monkeypatch, tmp_path):
    file_path = tmp_path / "track.mp3"
    file_path.touch()
    playlists_mock = Mock()
    monkeypatch.setattr(AppleMusicManager, "get_playlists", playlists_mock)

    success, message = AppleMusicManager.add_to_playlist(file_path, "   ")

    assert (success, message) == (False, "Please provide a playlist name.")
    playlists_mock.assert_not_called()


def test_add_to_playlist_resolves_name_case_insensitively_and_runs_script(monkeypatch, tmp_path):
    file_path = tmp_path / "track.mp3"
    file_path.touch()
    monkeypatch.setattr(
        AppleMusicManager,
        "get_playlists",
        lambda: (True, ["Roadtrip"], "Playlists retrieved"),
    )
    osascript_mock = Mock(return_value=(True, Mock(), ""))
    monkeypatch.setattr(AppleMusicManager, "_run_osascript", osascript_mock)

    success, message = AppleMusicManager.add_to_playlist(file_path, " roadTRIP ")

    assert (success, message) == (True, "Added to playlist 'Roadtrip'")
    script = osascript_mock.call_args.args[0]
    assert 'add sourcePath to playlist "Roadtrip"' in script


def test_add_to_playlist_reports_unknown_playlist_without_running_script(monkeypatch, tmp_path):
    file_path = tmp_path / "track.mp3"
    file_path.touch()
    monkeypatch.setattr(
        AppleMusicManager,
        "get_playlists",
        lambda: (True, ["Roadtrip"], "Playlists retrieved"),
    )
    osascript_mock = Mock()
    monkeypatch.setattr(AppleMusicManager, "_run_osascript", osascript_mock)

    success, message = AppleMusicManager.add_to_playlist(file_path, "Unknown")

    assert (success, message) == (
        False,
        'Playlist "Unknown" was not found in Apple Music. Please check the name and try again.',
    )
    osascript_mock.assert_not_called()
