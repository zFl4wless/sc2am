"""Tests for the external boundaries in SC2AM's download and Music workflows."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import sc2am.apple_music as apple_music
import sc2am.downloader as downloader_module
import main
from sc2am.apple_music import AppleMusicManager
from sc2am.downloader import Downloader
from click.testing import CliRunner


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


@pytest.mark.parametrize(
    ("missing", "install_command"),
    [("ffmpeg", "brew install ffmpeg"), ("ffprobe", "brew install ffmpeg")],
)
def test_downloader_rejects_missing_ffmpeg_tools(monkeypatch, tmp_path, missing, install_command):
    monkeypatch.setattr(
        downloader_module.shutil,
        "which",
        lambda executable: None if executable == missing else f"/usr/bin/{executable}",
    )

    with pytest.raises(RuntimeError, match=f"{missing} is not installed") as error:
        Downloader(tmp_path)

    assert install_command in str(error.value)


@pytest.mark.parametrize("failure", [FileExistsError, PermissionError])
def test_downloader_reports_download_directory_setup_failure(downloader, monkeypatch, failure):
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (True, {"title": "Track"}, "OK"))
    monkeypatch.setattr(
        downloader_module.Path,
        "mkdir",
        Mock(side_effect=failure("cannot create directory")),
    )

    assert downloader.download("https://soundcloud.com/artist/track") == (
        False,
        None,
        f"Could not create download directory '{downloader.download_dir}'. Check the path and permissions.",
    )


@pytest.mark.parametrize("command", ["download", "batch"])
@pytest.mark.parametrize("failure", ["file", "permission"])
def test_cli_reports_download_directory_failure_for_download_and_batch(
    command, failure, tmp_path, monkeypatch
):
    download_dir = tmp_path / "not-a-directory"
    if failure == "file":
        download_dir.touch()
    else:
        original_mkdir = downloader_module.Path.mkdir

        def deny_download_dir(path, *args, **kwargs):
            if path == download_dir:
                raise PermissionError("permission denied")
            return original_mkdir(path, *args, **kwargs)

        monkeypatch.setattr(downloader_module.Path, "mkdir", deny_download_dir)
    cfg = type(
        "Config",
        (),
        {
            "download_dir": download_dir,
            "open_music_app": False,
            "default_playlist": None,
            "continue_on_error": False,
        },
    )()
    monkeypatch.setattr(main, "_track_context", lambda *args: {"config": cfg, "logger": Mock()})
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    monkeypatch.setattr(
        Downloader,
        "get_track_info",
        staticmethod(lambda _: (True, {"title": "Track"}, "OK")),
    )
    runner = CliRunner()
    url = "https://soundcloud.com/artist/track"
    if command == "download":
        args = ["download", url, "--no-open", "--playlist", ""]
    else:
        batch_file = tmp_path / "urls.txt"
        batch_file.write_text(url + "\n")
        args = ["batch", str(batch_file), "--no-open", "--playlist", ""]

    result = runner.invoke(main.cli, args)

    assert result.exit_code == 1
    assert "Check the path and permissions." in result.output
    assert "Summary: 0 succeeded, 1 failed" in result.output


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
    assert command[:3] == ["yt-dlp", "--ignore-config", "--no-playlist"]
    assert "after_move:%(filepath)j" in command
    assert "--no-overwrites" in command
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
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (True, {"title": "Track"}, "OK"))
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
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (True, {"title": "Track"}, "OK"))
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
    downloader.metadata_writer = Mock()
    downloader.metadata_writer.write_to_file.return_value = (True, "OK")
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (True, {"title": "Track"}, "OK"))
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
        "Downloaded: retry.mp3 (metadata embedded)",
    )
    assert run_mock.call_count == 2
    sleep_mock.assert_called_once_with(Downloader._RETRY_DELAY_SECONDS)


def test_downloader_surfaces_unexpected_process_failure(downloader, monkeypatch):
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (True, {"title": "Track"}, "OK"))
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
        ["osascript", "-e", "test"], "Fetching playlists", read_only=True
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
        ["osascript", "-e", "test"], "Fetching playlists", read_only=True
    )

    assert (success, returned_result, error) == (True, results[1], "")
    assert run_mock.call_count == 2
    sleep_mock.assert_called_once_with(AppleMusicManager._RETRY_DELAY_SECONDS)


@pytest.mark.parametrize(
    "names",
    [
        ["Library", "Road, Trip", '音楽, "été"\\mix', "  Focus  ", "Line\nbreak", "Tab\tname"],
        ["Road, Trip", "Road, Trip"],
        ["Only one"],
        [],
    ],
)
def test_get_playlists_parses_osascript_output(monkeypatch, names):
    result = Mock(stdout=json.dumps(names, ensure_ascii=False) + "\n")
    monkeypatch.setattr(
        AppleMusicManager, "_run_osascript", lambda *args, **kwargs: (True, result, "")
    )

    success, playlists, message = AppleMusicManager.get_playlists()

    assert (success, playlists, message) == (
        True,
        names,
        "Playlists retrieved" if names else "No playlists found",
    )


@pytest.mark.parametrize("output", ["Road, Trip", "", '"Road, Trip"', "null", "{}", "[42]"])
def test_get_playlists_rejects_invalid_output(monkeypatch, output):
    monkeypatch.setattr(
        AppleMusicManager,
        "_run_osascript",
        lambda *args, **kwargs: (True, Mock(stdout=output), ""),
    )

    success, playlists, message = AppleMusicManager.get_playlists()

    assert (success, playlists) == (False, [])
    assert "Could not retrieve playlists" in message


@pytest.mark.parametrize(
    "names, requested, expected",
    [
        (["Road, Trip", "Road", "Trip"], "road, trip", "Road, Trip"),
        (['音楽, "été"\\mix'], '音楽, "ÉTÉ"\\mix', '音楽, "été"\\mix'),
        (["  Road, Trip  "], "Road, Trip", "  Road, Trip  "),
        (["Line\nbreak, mix"], "Line\nbreak, mix", "Line\nbreak, mix"),
    ],
)
def test_add_to_playlist_resolves_full_serialized_name(
    monkeypatch, tmp_path, names, requested, expected
):
    file_path = tmp_path / "track.mp3"
    file_path.touch()
    run_mock = Mock(
        side_effect=[
            Mock(returncode=0, stdout=json.dumps(names), stderr=""),
            Mock(returncode=0, stdout="", stderr=""),
        ]
    )
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)

    success, message = AppleMusicManager.add_to_playlist(file_path, requested)

    assert (success, message) == (True, f"Added to playlist '{expected}'")
    assert run_mock.call_count == 2
    assert run_mock.call_args.args[0][-2:] == [str(file_path.resolve()), expected]


@pytest.mark.parametrize("names", [["Road, Trip", "Road, Trip"], ["Road, Trip", "road, trip"]])
def test_serialized_duplicate_names_stop_import(monkeypatch, tmp_path, names):
    file_path = tmp_path / "track.mp3"
    file_path.touch()
    run_mock = Mock(return_value=Mock(returncode=0, stdout=json.dumps(names), stderr=""))
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)

    success, message = AppleMusicManager.add_to_playlist(file_path, "Road, Trip")

    assert success is False
    assert 'Multiple playlists named "Road, Trip"' in message
    assert "rename one" in message
    run_mock.assert_called_once()


def test_get_playlists_surfaces_automation_failure(monkeypatch):
    monkeypatch.setattr(
        AppleMusicManager,
        "_run_osascript",
        lambda *args, **kwargs: (False, Mock(), "Not authorised"),
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


def test_add_to_playlist_passes_absolute_path_and_playlist_as_exact_arguments(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    relative_directory = Path('folder "with quotes"\\東京')
    relative_directory.mkdir()
    file_path = relative_directory / 'mix "one"\\été.mp3'
    file_path.touch()
    playlist_name = 'Road "trip"\\音楽'
    monkeypatch.setattr(
        AppleMusicManager,
        "get_playlists",
        lambda: (True, [playlist_name], "Playlists retrieved"),
    )
    osascript_mock = Mock(return_value=(True, Mock(), ""))
    monkeypatch.setattr(AppleMusicManager, "_run_osascript", osascript_mock)

    success, message = AppleMusicManager.add_to_playlist(file_path, f" {playlist_name} ")

    assert (success, message) == (True, f"Added to playlist '{playlist_name}'")
    script, operation, arguments = osascript_mock.call_args.args
    assert operation == "Adding track to playlist"
    assert "on run argv" in script
    assert "set trackPath to item 1 of argv" in script
    assert "set targetPlaylist to item 2 of argv" in script
    assert f'"{file_path}"' not in script
    assert f'"{playlist_name}"' not in script
    assert arguments == [str(file_path.resolve()), playlist_name]


def test_playlist_import_selects_one_writable_object(monkeypatch, tmp_path):
    file_path = tmp_path / "track.mp3"
    file_path.touch()
    monkeypatch.setattr(AppleMusicManager, "get_playlists", lambda: (True, ["Road, Trip"], ""))
    osascript_mock = Mock(return_value=(True, Mock(), ""))
    monkeypatch.setattr(AppleMusicManager, "_run_osascript", osascript_mock)

    assert AppleMusicManager.add_to_playlist(file_path, "Road, Trip")[0]

    script = osascript_mock.call_args.args[0]
    assert "every playlist whose name is targetPlaylist" in script
    assert "(count of matchingPlaylists) is 0" in script
    assert "(count of matchingPlaylists) is greater than 1" in script
    assert "class of destinationPlaylist is not user playlist" in script
    assert "smart of destinationPlaylist" in script
    assert "genius of destinationPlaylist" in script
    assert "special kind of destinationPlaylist is not none" in script
    assert "add sourcePath to destinationPlaylist" in script
    assert script.index('error "Choose a regular user playlist;') < script.index(
        "add sourcePath to destinationPlaylist"
    )


@pytest.mark.parametrize(
    "error",
    [
        "The playlist no longer exists. Please check the playlist name.",
        "Multiple playlists have this name. Please rename one or choose a unique playlist name.",
        "Choose a regular user playlist that can receive tracks.",
        "Choose a regular user playlist; Smart, Genius, folder and system playlists cannot receive tracks.",
    ],
)
def test_playlist_target_validation_errors_are_actionable(monkeypatch, tmp_path, error):
    file_path = tmp_path / "track.mp3"
    file_path.touch()
    run_mock = Mock(
        side_effect=[
            Mock(returncode=0, stdout='["Road, Trip"]', stderr=""),
            Mock(returncode=1, stdout="", stderr=error),
        ]
    )
    monkeypatch.setattr(apple_music.subprocess, "run", run_mock)
    sleep_mock = Mock()
    monkeypatch.setattr(apple_music.time, "sleep", sleep_mock)

    success, message = AppleMusicManager.add_to_playlist(file_path, "Road, Trip")

    assert success is False
    assert "Failed to add the track to playlist 'Road, Trip'" in message
    assert error in message
    assert run_mock.call_count == 2
    sleep_mock.assert_not_called()


def test_run_osascript_appends_arguments_after_fixed_script(monkeypatch):
    run_mock = Mock(return_value=(True, Mock(), ""))
    monkeypatch.setattr(AppleMusicManager, "_run_command_with_retry", run_mock)
    script = "on run argv\nreturn item 1 of argv\nend run"
    arguments = ['path "quoted"\\音楽', 'playlist "quoted"\\été']

    result = AppleMusicManager._run_osascript(script, "test operation", arguments)

    assert result[0] is True
    run_mock.assert_called_once_with(
        ["osascript", "-e", script, *arguments],
        "test operation",
        read_only=False,
    )


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
