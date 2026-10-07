"""Exercise yt-dlp's actual filename expansion and reuse with local audio payloads."""

import contextlib
import io
from unittest.mock import Mock

import pytest
import yt_dlp

import sc2am.downloader as downloader_module
from sc2am.downloader import Downloader


@pytest.fixture
def local_downloads(tmp_path, monkeypatch):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    downloader.metadata_writer = Mock()
    downloader.metadata_writer.write_to_file.return_value = (True, "OK")
    tracks = {}

    def add_track(track_id, audio):
        source = tmp_path / f"source-{track_id}.mp3"
        source.write_bytes(audio)
        url = f"https://soundcloud.com/artist/track-{track_id}"
        tracks[url] = {
            "id": track_id,
            "title": "Intro",
            "artist": f"Artist {track_id}",
            "url": source.as_uri(),
            "ext": "mp3",
            "extractor": "soundcloud",
        }
        return url, source

    monkeypatch.setattr(downloader, "get_track_info", lambda url: (True, tracks[url], "OK"))

    def run(command, **kwargs):
        options = yt_dlp.parse_options(command[1:]).ydl_opts
        # Exercise real file downloads/reuse and after_move output, without FFmpeg
        # or network access. Audio conversion and SoundCloud extraction are out of scope.
        options.update(enable_file_urls=True, postprocessors=[], noupdate=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), yt_dlp.YoutubeDL(options) as ydl:
            ydl.process_ie_result(dict(tracks[command[-1]]), download=True)
        return Mock(returncode=0, stdout=output.getvalue(), stderr="")

    monkeypatch.setattr(downloader_module.subprocess, "run", run)
    return downloader, add_track, tracks


def test_identical_titles_with_different_ids_keep_separate_audio_and_tags(local_downloads):
    downloader, add_track, tracks = local_downloads
    first_url, _ = add_track("101", b"first recording")
    second_url, _ = add_track("202", b"second recording")
    downloader.download_dir.mkdir()
    legacy = downloader.download_dir / "Intro.mp3"
    legacy.write_bytes(b"legacy recording")

    first_ok, first_path, _ = downloader.download(first_url)
    second_ok, second_path, _ = downloader.download(second_url)

    assert first_ok and second_ok
    assert first_path.name == "Intro [101].mp3"
    assert second_path.name == "Intro [202].mp3"
    assert first_path.read_bytes() == b"first recording"
    assert second_path.read_bytes() == b"second recording"
    assert legacy.read_bytes() == b"legacy recording"
    assert [call.args for call in downloader.metadata_writer.write_to_file.call_args_list] == [
        (first_path, tracks[first_url]),
        (second_path, tracks[second_url]),
    ]


def test_repeat_download_reuses_audio_and_preserves_other_tracks(local_downloads):
    downloader, add_track, tracks = local_downloads
    url, source = add_track("101", b"original recording")
    other_url, _ = add_track("202", b"other recording")
    first_ok, first_path, _ = downloader.download(url)
    other_ok, other_path, _ = downloader.download(other_url)
    assert first_ok and other_ok
    source.unlink()  # Reuse must succeed without fetching the source audio again.
    tracks[url]["artist"] = "Updated artist"
    downloader.metadata_writer.reset_mock()

    success, path, message = downloader.download(url)

    assert success
    assert path == first_path
    assert message == "Reused verified download: Intro [101].mp3"
    assert path.read_bytes() == b"original recording"
    assert other_path.read_bytes() == b"other recording"
    assert len(list(downloader.download_dir.glob("*.mp3"))) == 2
    downloader.metadata_writer.write_to_file.assert_not_called()


def test_new_url_and_title_for_same_id_reuse_verified_path(local_downloads):
    downloader, add_track, tracks = local_downloads
    url, source = add_track("101", b"recording")
    assert downloader.download(url)[0]
    source.unlink()
    renamed = "https://soundcloud.com/artist/renamed-track"
    tracks[renamed] = {**tracks[url], "title": "Renamed"}
    success, path, message = downloader.download(renamed)
    assert success
    assert path.name == "Intro [101].mp3"
    assert "Reused verified download" in message
    assert len(list(downloader.download_dir.glob("*.mp3"))) == 1


def test_missing_cached_file_can_be_downloaded_again(local_downloads):
    downloader, add_track, _ = local_downloads
    url, _ = add_track("101", b"recording")
    success, path, _ = downloader.download(url)
    assert success
    path.unlink()
    success, restored, _ = downloader.download(url)
    assert success
    assert restored == path
    assert restored.read_bytes() == b"recording"


def test_changed_cached_file_is_never_retagged_or_reused(local_downloads):
    downloader, add_track, _ = local_downloads
    url, _ = add_track("101", b"recording")
    success, path, _ = downloader.download(url)
    assert success
    path.write_bytes(b"unrelated replacement")
    downloader.metadata_writer.reset_mock()
    success, result, message = downloader.download(url)
    assert not success
    assert result is None
    assert "file integrity" in message
    assert path.read_bytes() == b"unrelated replacement"
    downloader.metadata_writer.write_to_file.assert_not_called()


@pytest.mark.parametrize("value", [42, {"path": "x"}, ["bad"], {}, None])
def test_malformed_cache_record_returns_normal_error(local_downloads, value):
    from sc2am.history import History

    downloader, add_track, _ = local_downloads
    url, _ = add_track("101", b"recording")
    assert downloader.download(url)[0]
    with History(downloader.download_dir) as history:
        history.put("source:soundcloud:101", value)
    success, path, message = downloader.download(url)
    assert not success
    assert path is None
    assert "Could not verify the download history" in message
