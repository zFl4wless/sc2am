"""Run actual yt-dlp extraction and JSON loading against isolated local media."""

import contextlib
import io
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
import yt_dlp
from mutagen.id3 import ID3
from yt_dlp.extractor.common import InfoExtractor

import sc2am.downloader as module
from sc2am.downloader import Downloader
from sc2am.history import History


@pytest.mark.parametrize("broken_media", [False, True])
def test_one_extraction_supplies_audio_identity_and_tags(tmp_path, monkeypatch, broken_media):
    source = tmp_path / "source.mp3"
    source.write_bytes(b"isolated audio payload")
    url = "https://soundcloud.com/artist/track"
    extractions, commands, saved_info = [], [], []

    class LocalTrackIE(InfoExtractor):
        _VALID_URL = r"https://soundcloud\.com/artist/(?P<id>track)"

        def _real_extract(self, url):
            extractions.append(url)
            assert len(extractions) == 1, "A second extraction could now return a collection"
            return {
                "id": "123",
                "title": "Artist - Track",
                "artist": "Artist",
                "album": "Album",
                "album_artist": "Album artist",
                "genre": "Electronic",
                "release_date": "20261001",
                "track_number": 7,
                "thumbnail": "https://invalid.example/art.jpg",
                "formats": [{"url": source.as_uri(), "ext": "mp3", "format_id": "local"}],
            }

    monkeypatch.setattr(Downloader, "_check_dependencies", lambda _: None)
    downloader = Downloader(tmp_path / "downloads")
    monkeypatch.setattr(downloader, "_sleep_before_retry", lambda _: None)
    artwork = Mock(return_value="unavailable")
    monkeypatch.setattr(downloader.metadata_writer, "_write_cover_art", artwork)

    def run(command, **kwargs):
        commands.append(command)
        options = yt_dlp.parse_options(command[1:]).ydl_opts
        options.update(enable_file_urls=True, postprocessors=[], noupdate=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), yt_dlp.YoutubeDL(options, auto_init=False) as ydl:
            ydl.add_info_extractor(LocalTrackIE())
            if "--load-info-json" in command:
                saved_info.append(json.loads(Path(command[-1]).read_text()))
                assert "webpage_url" not in saved_info[-1]
                if broken_media:
                    source.unlink(missing_ok=True)
                try:
                    code = ydl.download_with_info_file(command[-1])
                except yt_dlp.utils.DownloadError:
                    return subprocess.CompletedProcess(command, 1, "", "HTTP Error 403")
            else:
                code = ydl.download([command[-1]])
        return subprocess.CompletedProcess(command, code, output.getvalue(), "")

    monkeypatch.setattr(module.subprocess, "run", run)
    success, path, message = downloader.download(url)
    assert len(extractions) == 1
    assert len(commands) == 2
    assert not Path(commands[-1][-1]).exists()
    assert saved_info[0]["formats"][0]["format_id"] == "local"
    if broken_media:
        assert not success and path is None
        artwork.assert_not_called()
        with History(downloader.download_dir) as history:
            assert history.get("url:" + url) is None
        assert not list(downloader.download_dir.glob("*.mp3"))
        return

    assert success, message
    assert path.name == "Artist - Track [123].mp3"
    tags = ID3(path)
    for key, text in {
        "TIT2": "Track",
        "TPE1": "Artist",
        "TALB": "Album",
        "TPE2": "Album artist",
        "TCON": "Electronic",
        "TDRC": "2026-10-01",
        "TRCK": "7",
    }.items():
        assert str(tags[key]) == text
    artwork.assert_called_once()
    assert artwork.call_args.args[1]["thumbnail"] == "https://invalid.example/art.jpg"
    with History(downloader.download_dir) as history:
        assert history.get("url:" + url) == "soundcloud:123"
    assert downloader.download(url)[0]
    assert len(commands) == 2  # Exact-URL resume neither extracts nor downloads nor retags.
    artwork.assert_called_once()


@pytest.mark.parametrize("failure", ["temporary", "timeout", "exception"])
def test_json_reuse_survives_retries_and_always_cleans_up(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(Downloader, "_check_dependencies", lambda _: None)
    downloader = Downloader(tmp_path / "downloads")
    info = {"id": "123", "title": "Track", "webpage_url": "https://soundcloud.com/artist/track"}
    get_info = Mock(return_value=(True, info, "OK"))
    monkeypatch.setattr(downloader, "get_track_info", get_info)
    monkeypatch.setattr(downloader, "_sleep_before_retry", lambda _: None)
    downloader.metadata_writer = Mock()
    downloader.metadata_writer.write_to_file.return_value = (True, "OK")
    paths = []

    def run(command, **kwargs):
        path = Path(command[-1])
        paths.append(path)
        assert json.loads(path.read_text()) == {"id": "123", "title": "Track"}
        if failure == "exception":
            raise OSError("process unavailable")
        if len(paths) == 1:
            if failure == "timeout":
                raise subprocess.TimeoutExpired(command, 300)
            return subprocess.CompletedProcess(command, 1, "", "Connection reset")
        mp3 = downloader.download_dir / "Track [123].mp3"
        mp3.write_bytes(b"audio")
        return subprocess.CompletedProcess(command, 0, json.dumps(str(mp3)), "")

    monkeypatch.setattr(module.subprocess, "run", run)
    success, _, _ = downloader.download(info["webpage_url"])
    assert success == (failure != "exception")
    get_info.assert_called_once()
    assert len(set(paths)) == 1
    assert not paths[0].exists()
    assert "webpage_url" in info  # Tagging uses the complete original metadata.
    if success:
        assert len(paths) == 2
        assert downloader.metadata_writer.write_to_file.call_args.args[1] == info


@pytest.mark.parametrize("tracks", [1, 10])
def test_isolated_benchmark_counts_fresh_and_resumed_external_work(tracks):
    import main
    from scripts.benchmark_workflow import measure

    fresh, resume = measure(main, tracks, command_delay=0, extraction_delay=0)
    assert fresh["calls"] == {
        "yt_dlp_processes": 2 * tracks,
        "url_extractions": tracks,
        "audio_downloads": tracks,
        "music_processes": 5 * tracks + 2,
        "playlist_listings": 1,
        "target_resolutions": 1,
        "music_mutations": 2 * tracks,
    }
    assert resume["calls"] == {
        "music_processes": 2 * tracks + 2,
        "playlist_listings": 1,
        "target_resolutions": 1,
    }


def test_temporary_info_failure_does_not_start_download_or_remember_source(tmp_path, monkeypatch):
    monkeypatch.setattr(Downloader, "_check_dependencies", lambda _: None)
    downloader = Downloader(tmp_path / "downloads")
    url = "https://soundcloud.com/artist/track"
    monkeypatch.setattr(downloader, "get_track_info", lambda _: (True, {"id": "123"}, "OK"))
    monkeypatch.setattr(
        module.tempfile, "NamedTemporaryFile", Mock(side_effect=OSError("disk full"))
    )
    run = Mock()
    monkeypatch.setattr(module.subprocess, "run", run)
    success, path, error = downloader.download(url)
    assert not success and path is None
    assert "temporary directory space and permissions" in error
    run.assert_not_called()
    with History(downloader.download_dir) as history:
        assert history.get("url:" + url) is None
