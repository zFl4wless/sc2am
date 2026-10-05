"""Reject collections before any audio download or Music action can occur."""

import json
import contextlib
import io
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
import yt_dlp
from yt_dlp.extractor.common import InfoExtractor

import main
import sc2am.downloader as downloader_module
from sc2am.downloader import Downloader
from sc2am.validator import URLValidator

COLLECTION_PATHS = [
    "artist",
    "artist/likes",
    "artist/sets",
    "artist/reposts",
    "artist/tracks",
    "artist/albums",
    "artist/spotlight",
    "artist/comments",
    "artist/sets/mix",
    "artist/%6cikes",
]


@pytest.mark.parametrize("path", COLLECTION_PATHS)
def test_collection_routes_are_rejected_at_every_entry_point(tmp_path, monkeypatch, path):
    url = f"https://soundcloud.com/{path}"
    assert URLValidator.validate_url(url) == (False, URLValidator.SOUNDCLOUD_TRACK_HELP)
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(url + "\n")
    assert URLValidator.validate_batch_file(str(batch_file)) == (
        False,
        [],
        [(1, URLValidator.SOUNDCLOUD_TRACK_HELP)],
    )
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    run_mock = Mock()
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)
    assert downloader.download(url) == (False, None, URLValidator.SOUNDCLOUD_TRACK_HELP)
    assert Downloader.get_track_info(url) == (False, None, URLValidator.SOUNDCLOUD_TRACK_HELP)
    run_mock.assert_not_called()
    assert not downloader.download_dir.exists()


@pytest.mark.parametrize(
    "url",
    [
        "https://soundcloud.com/artist/track",
        "https://www.soundcloud.com/artist/track/?in=artist/sets/mix",
        "soundcloud.com/artist/likes-remix",
    ],
)
def test_single_track_urls_remain_supported(url):
    assert URLValidator.validate_url(url) == (True, "SoundCloud")


@pytest.mark.parametrize("command", ["download", "batch"])
def test_cli_rejects_profile_routes_without_preparing_downloads(tmp_path, monkeypatch, command):
    url = "https://soundcloud.com/artist/likes"
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(url + "\n")
    downloader_factory, music_factory = Mock(), Mock()
    monkeypatch.setattr(main, "_create_downloader", downloader_factory)
    monkeypatch.setattr(main, "AppleMusicManager", music_factory)

    result = CliRunner().invoke(
        main.cli, [command, url if command == "download" else str(batch_file)]
    )

    assert result.exit_code == 2, result.output
    assert URLValidator.SOUNDCLOUD_TRACK_HELP in result.output
    downloader_factory.assert_not_called()
    music_factory.assert_not_called()


@pytest.mark.parametrize(
    "info",
    [
        {"_type": "playlist", "entries": []},
        {"_type": "playlist", "entries": [{"id": "123"}]},
        {"_type": "multi_video", "entries": [{"id": "123"}]},
        {"entries": []},
        {"_type": "url", "url": "https://soundcloud.com/artist/likes"},
        [],
        None,
    ],
)
def test_extracted_collections_never_download_tag_or_import(tmp_path, monkeypatch, info):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    downloader.metadata_writer = Mock()
    run_mock = Mock(return_value=Mock(returncode=0, stdout=json.dumps(info), stderr=""))
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)
    monkeypatch.setattr(main, "_create_downloader", lambda *args: downloader)
    music_factory = Mock()
    monkeypatch.setattr(main, "AppleMusicManager", music_factory)

    result = CliRunner().invoke(main.cli, ["download", "https://soundcloud.com/artist/track"])

    assert result.exit_code == 1, result.output
    assert URLValidator.SOUNDCLOUD_TRACK_HELP in result.output
    run_mock.assert_called_once()
    command = run_mock.call_args.args[0]
    assert "--dump-single-json" in command
    assert "--flat-playlist" in command
    assert command[command.index("--playlist-end") + 1] == "1"
    downloader.metadata_writer.write_to_file.assert_not_called()
    music_factory.assert_not_called()
    assert not downloader.download_dir.exists()


@pytest.mark.parametrize("output", ["not json", "{}\n{}"])
def test_unreadable_preflight_aborts_without_downloading(tmp_path, monkeypatch, output):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    monkeypatch.setattr(downloader_module.time, "sleep", lambda _: None)
    run_mock = Mock(return_value=Mock(returncode=0, stdout=output, stderr=""))
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)

    assert downloader.download("https://soundcloud.com/artist/track") == (
        False,
        None,
        "Could not read track information from yt-dlp.",
    )
    assert run_mock.call_count == Downloader._MAX_RETRIES
    assert all("--dump-single-json" in call.args[0] for call in run_mock.call_args_list)
    assert not downloader.download_dir.exists()


def test_real_yt_dlp_preflight_preserves_collection_without_extracting_entries(
    tmp_path, monkeypatch
):
    class CollectionIE(InfoExtractor):
        _VALID_URL = r"https://soundcloud\.com/artist/(?P<id>track)"

        def _real_extract(self, url):
            return self.playlist_result(
                [self.url_result("https://invalid.example/audio", ie="MissingExtractor")],
                "collection",
            )

    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")

    def run(command, **kwargs):
        options = yt_dlp.parse_options(["--ignore-config", *command[1:]]).ydl_opts
        output = io.StringIO()
        with contextlib.redirect_stdout(output), yt_dlp.YoutubeDL(options, auto_init=False) as ydl:
            ydl.add_info_extractor(CollectionIE())
            assert ydl.download([command[-1]]) == 0
        return Mock(returncode=0, stdout=output.getvalue(), stderr="")

    run_mock = Mock(side_effect=run)
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)

    assert downloader.download("https://soundcloud.com/artist/track") == (
        False,
        None,
        URLValidator.SOUNDCLOUD_TRACK_HELP,
    )
    run_mock.assert_called_once()
    assert not downloader.download_dir.exists()


def test_failed_preflight_never_starts_audio_download(tmp_path, monkeypatch):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    run_mock = Mock(return_value=Mock(returncode=1, stdout="", stderr="HTTP Error 403"))
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)

    success, path, message = downloader.download("https://soundcloud.com/artist/track")

    assert (success, path) == (False, None)
    assert "Please use a public SoundCloud track URL." in message
    run_mock.assert_called_once()
    assert "--dump-single-json" in run_mock.call_args.args[0]
    assert not downloader.download_dir.exists()
