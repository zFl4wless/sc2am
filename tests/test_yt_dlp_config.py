"""Exercise both SC2AM commands with conflicting external yt-dlp configs."""

import contextlib
import io
import shlex
import sys
from unittest.mock import Mock

import pytest
import yt_dlp
import yt_dlp.options
from yt_dlp.extractor.common import InfoExtractor

import sc2am.downloader as downloader_module
from sc2am.downloader import Downloader


@pytest.mark.parametrize("location", ["portable", "home", "user", "system"])
@pytest.mark.parametrize("setting", ["skip-download", "archive", "filter"])
def test_external_config_cannot_skip_metadata_or_audio(tmp_path, monkeypatch, location, setting):
    config_dirs = {name: tmp_path / name for name in ("portable", "home", "user", "system")}
    for directory in config_dirs.values():
        directory.mkdir()
    monkeypatch.chdir(config_dirs["home"])
    monkeypatch.setattr(yt_dlp.options, "get_executable_path", lambda: str(config_dirs["portable"]))
    monkeypatch.setattr(
        yt_dlp.options, "get_user_config_dirs", lambda _: [str(config_dirs["user"] / "yt-dlp")]
    )
    monkeypatch.setattr(
        yt_dlp.options, "get_system_config_dirs", lambda _: [str(config_dirs["system"] / "yt-dlp")]
    )
    archive = tmp_path / "archive.txt"
    archive.write_text("localtrack 123\n")
    settings = {
        "skip-download": "--skip-download\n",
        "archive": f"--download-archive {shlex.quote(str(archive))}\n",
        "filter": '--match-filter "title = Rejected"\n',
    }
    (config_dirs[location] / "yt-dlp.conf").write_text(settings[setting])
    source = tmp_path / "source.mp3"
    source.write_bytes(b"local recording")
    url = "https://soundcloud.com/artist/track"
    track_info = {"id": "123", "title": "Track", "url": source.as_uri(), "ext": "mp3"}

    class LocalTrackIE(InfoExtractor):
        _VALID_URL = r"https://soundcloud\.com/artist/(?P<id>track)"

        def _real_extract(self, url):
            return dict(track_info)

    # Use CLI parsing without override arguments, which otherwise disables config
    # loading by default in yt-dlp's Python API. Confirm the conflict is discoverable.
    monkeypatch.setattr(sys, "argv", ["yt-dlp", url])
    conflicting = yt_dlp.parse_options().ydl_opts
    if setting == "skip-download":
        assert conflicting["skip_download"] is True
    elif setting == "archive":
        assert conflicting["download_archive"] == str(archive)
    else:
        assert conflicting["match_filter"] is not None

    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    downloader.metadata_writer = Mock()
    downloader.metadata_writer.write_to_file.return_value = (True, "OK")

    def run(command, **kwargs):
        monkeypatch.setattr(sys, "argv", command)
        options = yt_dlp.parse_options().ydl_opts
        assert "--ignore-config" in command
        assert options["skip_download"] is False
        assert options["download_archive"] is None
        assert options["match_filter"] is None
        # Keep extraction and file downloading real, with a local fixture extractor
        # and no FFmpeg conversion (the payload is already an MP3 test fixture).
        options.update(enable_file_urls=True, postprocessors=[], noupdate=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), yt_dlp.YoutubeDL(options, auto_init=False) as ydl:
            ydl.add_info_extractor(LocalTrackIE())
            assert ydl.download([command[-1]]) == 0
        return Mock(returncode=0, stdout=output.getvalue(), stderr="")

    run_mock = Mock(side_effect=run)
    monkeypatch.setattr(downloader_module.subprocess, "run", run_mock)

    success, path, message = downloader.download(url)

    assert success, message
    assert path == downloader.download_dir / "Track [123].mp3"
    assert path.read_bytes() == source.read_bytes()
    assert run_mock.call_count == 2
    assert "--dump-single-json" in run_mock.call_args_list[0].args[0]
    assert "--extract-audio" in run_mock.call_args_list[1].args[0]
    written_path, metadata = downloader.metadata_writer.write_to_file.call_args.args
    assert written_path == path
    assert metadata["id"] == "123"
    assert metadata["title"] == "Track"
    assert archive.read_text() == "localtrack 123\n"
