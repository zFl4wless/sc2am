"""Resolve mobile share links without live HTTP, downloads, or Music actions."""

import json
from unittest.mock import Mock

import pytest
import requests
from click.testing import CliRunner

import main
import sc2am.downloader as downloader_module
import sc2am.validator as validator_module
from sc2am.downloader import Downloader
from sc2am.validator import URLValidator

SHARE = "https://on.soundcloud.com/token"
TRACK = "https://soundcloud.com/artist/track?si=share&in=artist/sets/mix"


def response(status=302, location=TRACK):
    result = Mock(status_code=status, headers={} if location is None else {"Location": location})
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result


@pytest.fixture
def head(monkeypatch):
    request = Mock(return_value=response())
    monkeypatch.setattr(validator_module.requests, "head", request)
    return request


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("url", [SHARE, "on.soundcloud.com/token", "  " + SHARE + "  "])
def test_share_resolves_to_track_with_query_preserved(head, status, url):
    reply = response(status)
    head.return_value = reply
    assert URLValidator.resolve_track_url(url) == (True, TRACK, "SoundCloud")
    head.assert_called_once_with(
        SHARE, allow_redirects=False, timeout=URLValidator.SHARE_TIMEOUT, stream=True
    )
    reply.__exit__.assert_called_once()


def test_legacy_validation_api_accepts_share_link(head):
    assert URLValidator.validate_url(SHARE) == (True, "SoundCloud")
    head.assert_called_once()


def test_relative_and_protocol_relative_redirects(head):
    replies = [response(location="/second"), response(location="//www.soundcloud.com/a/b")]
    head.side_effect = replies
    assert URLValidator.resolve_track_url(SHARE) == (
        True,
        "https://www.soundcloud.com/a/b",
        "SoundCloud",
    )
    assert [call.args[0] for call in head.call_args_list] == [
        SHARE,
        "https://on.soundcloud.com/second",
    ]
    assert all(reply.__exit__.call_count == 1 for reply in replies)


@pytest.mark.parametrize("status", [404, 410])
def test_expired_share_links(head, status):
    head.return_value = response(status, None)
    valid, target, message = URLValidator.resolve_track_url(SHARE)
    assert (valid, target) == (False, "")
    assert "expired or was not found" in message
    assert URLValidator.SHARE_HELP in message
    head.assert_called_once()


@pytest.mark.parametrize("status", [200, 204, 403, 405, 429, 500, 503])
def test_non_redirect_responses_have_actionable_http_error(head, status):
    head.return_value = response(status)
    valid, _, message = URLValidator.resolve_track_url(SHARE)
    assert not valid
    assert f"HTTP {status}" in message
    assert URLValidator.SHARE_HELP in message
    head.assert_called_once()


@pytest.mark.parametrize("location", [None, "", "   "])
def test_redirect_without_target(head, location):
    head.return_value = response(location=location)
    valid, _, message = URLValidator.resolve_track_url(SHARE)
    assert not valid
    assert "without a target" in message


@pytest.mark.parametrize(
    "target",
    [
        "https://example.org/a/b",
        "https://soundcloud.com.example.org/a/b",
        "https://on.soundcloud.com.example.org/token",
        "https://soundcloud.com@evil.example/a/b",
        "https://user:password@soundcloud.com/a/b",
        "https://on.soundcloud.com:8443/token",
        "https://soundcloud.com:8443/a/b",
        "file:///etc/passwd",
        "ftp://soundcloud.com/a/b",
        "https://soundcloud.com/a/track with space",
    ],
)
def test_unexpected_redirects_are_rejected_before_requesting_target(head, target):
    head.return_value = response(location=target)
    valid, _, message = URLValidator.resolve_track_url(SHARE)
    assert not valid
    assert "unsupported URL" in message
    assert URLValidator.SHARE_HELP in message
    head.assert_called_once()


@pytest.mark.parametrize("target", ["https://[invalid", "https://soundcloud.com:bad/a/b"])
def test_malformed_redirects_have_useful_error(head, target):
    head.return_value = response(location=target)
    valid, _, message = URLValidator.resolve_track_url(SHARE)
    assert not valid
    assert "invalid URL" in message
    head.assert_called_once()


@pytest.mark.parametrize(
    "url", ["https://user@on.soundcloud.com/token", "https://on.soundcloud.com:8443/token"]
)
def test_unsafe_initial_share_url_never_requests(head, url):
    assert not URLValidator.resolve_track_url(url)[0]
    head.assert_not_called()


@pytest.mark.parametrize("target", [SHARE, SHARE + "#new-fragment"])
def test_redirect_loop_is_detected_without_repeating_request(head, target):
    head.return_value = response(location=target)
    valid, _, message = URLValidator.resolve_track_url(SHARE)
    assert not valid
    assert "redirect loop" in message
    head.assert_called_once()


def test_two_link_loop(head):
    head.side_effect = [response(location="/second"), response(location=SHARE)]
    assert "redirect loop" in URLValidator.resolve_track_url(SHARE)[2]
    assert head.call_count == 2


def test_redirect_request_limit(head):
    head.side_effect = [
        response(location=f"/hop-{n}") for n in range(URLValidator.SHARE_MAX_REQUESTS)
    ]
    valid, _, message = URLValidator.resolve_track_url(SHARE)
    assert not valid
    assert "redirect limit" in message
    assert head.call_count == URLValidator.SHARE_MAX_REQUESTS


def test_final_allowed_request_can_resolve_track(head):
    head.side_effect = [
        response(location=f"/hop-{n}") for n in range(URLValidator.SHARE_MAX_REQUESTS - 1)
    ] + [response()]
    assert URLValidator.resolve_track_url(SHARE) == (True, TRACK, "SoundCloud")
    assert head.call_count == URLValidator.SHARE_MAX_REQUESTS


@pytest.mark.parametrize(
    "error", [requests.Timeout(), requests.ConnectionError(), requests.TooManyRedirects()]
)
def test_network_errors_are_actionable_and_do_not_retry(head, error):
    head.side_effect = error
    valid, _, message = URLValidator.resolve_track_url(SHARE)
    assert not valid
    assert "Check your connection and try again" in message
    assert URLValidator.SHARE_HELP in message
    head.assert_called_once()


@pytest.mark.parametrize(
    "path", ["artist", "artist/likes", "artist/%73ets", "artist/sets/mix", "artist/tracks"]
)
def test_share_links_to_collections_are_rejected(head, path):
    head.return_value = response(location=f"https://soundcloud.com/{path}")
    assert URLValidator.validate_url(SHARE) == (False, URLValidator.SOUNDCLOUD_TRACK_HELP)
    head.assert_called_once()


@pytest.mark.parametrize(
    "url",
    [
        TRACK,
        "soundcloud.com/artist/track",
        "https://soundcloud.com/artist/sets",
        "https://example.org/a/b",
    ],
)
def test_direct_urls_never_make_http_requests(head, url):
    URLValidator.resolve_track_url(url)
    head.assert_not_called()


def test_batch_returns_resolved_urls_and_line_errors(tmp_path, head):
    head.side_effect = [response(), response(410, None)]
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(f"# tracks\n\n{SHARE}\n{SHARE}/expired\n{TRACK}\n", encoding="utf-8")
    valid, urls, errors = URLValidator.validate_batch_file(str(batch_file))
    assert not valid
    assert urls == [TRACK, TRACK]
    assert errors[0][0] == 4
    assert "expired" in errors[0][1]
    assert head.call_count == 2


@pytest.mark.parametrize("command", ["download", "batch"])
def test_cli_passes_resolved_track_to_downloader(tmp_path, monkeypatch, head, command):
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(SHARE + "\n", encoding="utf-8")
    downloader = Mock()
    downloader.download.return_value = (True, tmp_path / "track.mp3", "Downloaded")
    monkeypatch.setattr(main, "_create_downloader", lambda *args: downloader)
    music = Mock()
    monkeypatch.setattr(main, "AppleMusicManager", music)
    result = CliRunner().invoke(
        main.cli,
        [
            command,
            SHARE if command == "download" else str(batch_file),
            "--no-open",
            "--playlist",
            "",
        ],
    )
    assert result.exit_code == 0, result.output
    downloader.download.assert_called_once_with(TRACK)
    head.assert_called_once()
    music.assert_not_called()


@pytest.mark.parametrize("command", ["download", "batch"])
def test_dry_run_resolves_share_without_preparing_download_or_music(
    tmp_path, monkeypatch, head, command
):
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(SHARE + "\n", encoding="utf-8")
    downloader, music = Mock(), Mock()
    monkeypatch.setattr(main, "_create_downloader", downloader)
    monkeypatch.setattr(main, "AppleMusicManager", music)
    result = CliRunner().invoke(
        main.cli, [command, SHARE if command == "download" else str(batch_file), "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    head.assert_called_once()
    downloader.assert_not_called()
    music.assert_not_called()


@pytest.mark.parametrize("command", ["download", "batch"])
@pytest.mark.parametrize(
    "reply",
    [
        response(location="https://soundcloud.com/artist/sets/mix"),
        response(location="https://example.org/a/b"),
        response(410, None),
    ],
)
def test_cli_rejects_share_before_any_download_or_music(
    tmp_path, monkeypatch, head, command, reply
):
    head.return_value = reply
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(SHARE + "\n", encoding="utf-8")
    downloader, music = Mock(), Mock()
    monkeypatch.setattr(main, "_create_downloader", downloader)
    monkeypatch.setattr(main, "AppleMusicManager", music)
    result = CliRunner().invoke(
        main.cli, [command, SHARE if command == "download" else str(batch_file)]
    )
    assert result.exit_code == 2, result.output
    assert "ERROR:" in result.output
    downloader.assert_not_called()
    music.assert_not_called()


def test_track_info_extraction_uses_resolved_url(monkeypatch, head):
    run = Mock(return_value=Mock(returncode=0, stdout=json.dumps({"id": "123"}), stderr=""))
    monkeypatch.setattr(downloader_module.subprocess, "run", run)
    assert Downloader.get_track_info(SHARE)[0]
    assert run.call_args.args[0][-1] == TRACK
    head.assert_called_once()


def test_download_and_history_use_resolved_url(tmp_path, monkeypatch, head):
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    downloader.metadata_writer = Mock()
    downloader.metadata_writer.write_to_file.return_value = (True, "OK")
    downloader.download_dir.mkdir()
    mp3 = downloader.download_dir / "track [123].mp3"
    mp3.write_bytes(b"verified test MP3")
    run = Mock(
        side_effect=[
            Mock(returncode=0, stdout=json.dumps({"id": "123"}), stderr=""),
            Mock(returncode=0, stdout=json.dumps(str(mp3)), stderr=""),
        ]
    )
    monkeypatch.setattr(downloader_module.subprocess, "run", run)
    assert downloader.download(SHARE)[0]
    assert [call.args[0][-1] for call in run.call_args_list] == [TRACK, TRACK]
    head.assert_called_once()
    run.reset_mock()
    assert downloader.download(TRACK)[0]
    run.assert_not_called()


@pytest.mark.parametrize("method", ["download", "get_track_info"])
def test_downloader_rejects_share_collection_before_extraction(tmp_path, monkeypatch, head, method):
    head.return_value = response(location="https://soundcloud.com/artist/sets/mix")
    monkeypatch.setattr(Downloader, "_check_dependencies", staticmethod(lambda: None))
    downloader = Downloader(tmp_path / "downloads")
    run = Mock()
    monkeypatch.setattr(downloader_module.subprocess, "run", run)
    assert getattr(downloader, method)(SHARE) == (False, None, URLValidator.SOUNDCLOUD_TRACK_HELP)
    run.assert_not_called()
    assert not downloader.download_dir.exists()


def test_malformed_direct_url_keeps_existing_error(head):
    assert URLValidator.validate_url("https://[invalid") == (
        False,
        "The URL could not be parsed. Please check the format and try again.",
    )
    head.assert_not_called()


def test_batch_can_skip_expired_share_and_download_resolved_track(tmp_path, monkeypatch, head):
    head.side_effect = [response(410, None), response()]
    batch_file = tmp_path / "urls.txt"
    batch_file.write_text(f"{SHARE}/expired\n{SHARE}\n", encoding="utf-8")
    downloader = Mock()
    downloader.download.return_value = (True, tmp_path / "track.mp3", "Downloaded")
    monkeypatch.setattr(main, "_create_downloader", lambda *args: downloader)
    music = Mock()
    monkeypatch.setattr(main, "AppleMusicManager", music)
    result = CliRunner().invoke(
        main.cli, ["batch", str(batch_file), "--continue-on-error", "--no-open", "--playlist", ""]
    )
    assert result.exit_code == 1, result.output
    assert "Line 1:" in result.output
    assert "1 succeeded, 1 failed" in result.output
    downloader.download.assert_called_once_with(TRACK)
    assert head.call_count == 2
    music.assert_not_called()
