import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock
from unittest import mock

import click

import main
from main import _exit_with_error, _track_label, _track_status
import sc2am.apple_music as apple_music
import sc2am.downloader as downloader_module
from sc2am.apple_music import AppleMusicManager
from sc2am.downloader import Downloader
from sc2am.validator import URLValidator


class ErrorMessageTests(unittest.TestCase):
    def test_empty_url_is_rejected_with_helpful_message(self):
        is_valid, message = URLValidator.validate_url("")

        self.assertFalse(is_valid)
        self.assertEqual(message, "Please provide a valid URL.")

    def test_non_soundcloud_urls_are_rejected(self):
        is_valid, message = URLValidator.validate_url("https://youtube.com/watch?v=123")

        self.assertFalse(is_valid)
        self.assertEqual(message, "Only SoundCloud track URLs are supported right now.")

    def test_soundcloud_track_url_is_accepted(self):
        is_valid, message = URLValidator.validate_url("https://soundcloud.com/artist/track")

        self.assertTrue(is_valid)
        self.assertEqual(message, "SoundCloud")

    def test_downloader_classifies_missing_track_as_user_friendly_error(self):
        message = Downloader._classify_download_error("HTTP Error 404: Not Found")

        self.assertEqual(
            message,
            "The track could not be found. It may have been removed or the link may be wrong.",
        )

    def test_downloader_retries_temporary_failure_before_succeeding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            file_path = download_dir / "track.mp3"
            file_path.touch()

            with mock.patch.object(Downloader, "_check_dependencies"):
                downloader = Downloader(download_dir)

            first_attempt = Mock(returncode=1, stdout="", stderr="HTTP Error 503: Service Unavailable")
            second_attempt = Mock(returncode=0, stdout=f"{file_path}\n", stderr="")

            with mock.patch.object(downloader, "get_track_info", return_value=(True, None, "Info fetched successfully")), \
                mock.patch.object(downloader_module.subprocess, "run", side_effect=[first_attempt, second_attempt]) as run_mock, \
                mock.patch.object(downloader_module.time, "sleep") as sleep_mock:
                success, result_path, message = downloader.download("https://soundcloud.com/artist/track")

        self.assertTrue(success)
        self.assertEqual(result_path, file_path)
        self.assertEqual(message, f"Downloaded: {file_path.name}")
        self.assertEqual(run_mock.call_count, 2)
        sleep_mock.assert_called_once()

    def test_downloader_does_not_retry_permanent_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()

            with mock.patch.object(Downloader, "_check_dependencies"):
                downloader = Downloader(download_dir)

            failure = Mock(returncode=1, stdout="", stderr="HTTP Error 404: Not Found")

            with mock.patch.object(downloader, "get_track_info", return_value=(True, None, "Info fetched successfully")), \
                mock.patch.object(downloader_module.subprocess, "run", return_value=failure) as run_mock, \
                mock.patch.object(downloader_module.time, "sleep") as sleep_mock:
                success, result_path, message = downloader.download("https://soundcloud.com/artist/track")

        self.assertFalse(success)
        self.assertIsNone(result_path)
        self.assertEqual(
            message,
            "The track could not be found. It may have been removed or the link may be wrong.",
        )
        self.assertEqual(run_mock.call_count, 1)
        sleep_mock.assert_not_called()

    def test_missing_music_file_returns_clear_error(self):
        success, message = AppleMusicManager.open_file_with_music(Path("/tmp/does-not-exist.mp3"))

        self.assertFalse(success)
        self.assertEqual(message, "The downloaded file was not found.")

    def test_open_file_with_music_retries_temporary_failure_before_succeeding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()

            first_attempt = Mock(returncode=1, stdout="", stderr="AppleEvent timed out")
            second_attempt = Mock(returncode=0, stdout="", stderr="")

            with mock.patch.object(apple_music.subprocess, "run", side_effect=[first_attempt, second_attempt]) as run_mock, \
                mock.patch.object(apple_music.time, "sleep") as sleep_mock:
                success, message = AppleMusicManager.open_file_with_music(file_path)

        self.assertTrue(success)
        self.assertEqual(message, "Opened with Apple Music")
        self.assertEqual(run_mock.call_count, 2)
        sleep_mock.assert_called_once()

    def test_missing_playlist_file_returns_clear_error(self):
        success, message = AppleMusicManager.add_to_playlist(
            Path("/tmp/does-not-exist.mp3"),
            "My Playlist",
        )

        self.assertFalse(success)
        self.assertEqual(message, "The downloaded file was not found.")

    def test_missing_playlist_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()

            with mock.patch.object(
                AppleMusicManager,
                "get_playlists",
                return_value=(True, ["Roadtrip", "Focus"], "Playlists retrieved"),
            ), mock.patch.object(apple_music.subprocess, "run") as run_mock:
                success, message = AppleMusicManager.add_to_playlist(
                    file_path,
                    "Workout",
                )

        self.assertFalse(success)
        self.assertEqual(
            message,
            'Playlist "Workout" was not found in Apple Music. Please check the name and try again.',
        )
        run_mock.assert_not_called()

    def test_duplicate_playlist_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()

            with mock.patch.object(
                AppleMusicManager,
                "get_playlists",
                return_value=(True, ["Roadtrip", "Roadtrip", "Focus"], "Playlists retrieved"),
            ), mock.patch.object(apple_music.subprocess, "run") as run_mock:
                success, message = AppleMusicManager.add_to_playlist(
                    file_path,
                    "Roadtrip",
                )

        self.assertFalse(success)
        self.assertEqual(
            message,
            'Multiple playlists named "Roadtrip" were found in Apple Music. Please rename one of them or choose a unique playlist name.',
        )
        run_mock.assert_not_called()

    def test_add_to_playlist_uses_the_resolved_playlist_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()

            with mock.patch.object(
                AppleMusicManager,
                "get_playlists",
                return_value=(True, ["Roadtrip", "Focus"], "Playlists retrieved"),
            ), mock.patch.object(apple_music.subprocess, "run") as run_mock:
                run_mock.return_value.returncode = 0
                run_mock.return_value.stderr = ""
                success, message = AppleMusicManager.add_to_playlist(
                    file_path,
                    "  roadtrip  ",
                )

        self.assertTrue(success)
        self.assertEqual(message, "Added to playlist 'Roadtrip'")
        self.assertTrue(run_mock.called)

    def test_add_to_playlist_retries_temporary_failure_before_succeeding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()

            first_attempt = Mock(returncode=1, stdout="", stderr="AppleEvent timed out")
            second_attempt = Mock(returncode=0, stdout="", stderr="")

            with mock.patch.object(
                AppleMusicManager,
                "get_playlists",
                return_value=(True, ["Roadtrip"], "Playlists retrieved"),
            ), mock.patch.object(apple_music.subprocess, "run", side_effect=[first_attempt, second_attempt]) as run_mock, \
                mock.patch.object(apple_music.time, "sleep") as sleep_mock:
                success, message = AppleMusicManager.add_to_playlist(file_path, "Roadtrip")

        self.assertTrue(success)
        self.assertEqual(message, "Added to playlist 'Roadtrip'")
        self.assertEqual(run_mock.call_count, 2)
        sleep_mock.assert_called_once()

    def test_exit_helper_raises_click_exception(self):
        logger = Mock()

        with self.assertRaises(click.ClickException) as ctx:
            _exit_with_error(logger, "Something went wrong.")

        self.assertEqual(str(ctx.exception), "Something went wrong.")
        logger.error.assert_called_once_with("Something went wrong.")

    def test_track_label_formats_single_and_batch_tracks(self):
        self.assertEqual(_track_label(), "Track")
        self.assertEqual(_track_label(2, 5), "Track 2/5")

    def test_track_status_logs_with_matching_severity(self):
        logger = Mock()

        with mock.patch.object(click, "secho") as secho_mock:
            _track_status(logger, "Track 1/1", "ERROR: Failed", fg="red", level="error")

        secho_mock.assert_called_once_with("Track 1/1: ERROR: Failed", fg="red", bold=False)
        logger.log.assert_called_once()
        log_args = logger.log.call_args.args
        self.assertEqual(log_args[0], main.logging.ERROR)
        self.assertEqual(log_args[1], "Track 1/1: ERROR: Failed")

    def test_run_summary_reports_success_and_failure_counts(self):
        logger = Mock()

        with mock.patch.object(click, "secho") as secho_mock:
            main._print_run_summary(logger, 3, 1)

        secho_mock.assert_called_once_with("Summary: 3 succeeded, 1 failed", fg="yellow", bold=True)
        logger.info.assert_called_once_with("Summary: 3 succeeded, 1 failed")

    def test_download_shows_final_summary_for_successful_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            file_path = download_dir / "track.mp3"
            file_path.touch()

            cfg = Mock(download_dir=download_dir, open_music_app=False, default_playlist=None)
            logger = Mock()
            ctx = mock.Mock()
            ctx.obj = {"config": cfg, "logger": logger}

            downloader = Mock()
            downloader.download.return_value = (True, file_path, "Downloaded: track.mp3")

            download_cmd = cast(Any, main.download)
            with mock.patch.object(main.URLValidator, "validate_url", return_value=(True, "SoundCloud")), \
                mock.patch.object(main, "_create_downloader", return_value=downloader), \
                mock.patch.object(click, "secho") as secho_mock:
                download_cmd.callback.__wrapped__(
                    ctx,
                    ("https://soundcloud.com/artist/track",),
                    None,
                    True,
                    False,
                )

        secho_mock.assert_any_call("Summary: 1 succeeded, 0 failed", fg="green", bold=True)

    def test_download_processes_multiple_links_in_one_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            file_one = download_dir / "one.mp3"
            file_two = download_dir / "two.mp3"
            file_one.touch()
            file_two.touch()

            cfg = Mock(download_dir=download_dir, open_music_app=False, default_playlist=None)
            logger = Mock()
            ctx = mock.Mock()
            ctx.obj = {"config": cfg, "logger": logger}

            downloader = Mock()
            downloader.download.side_effect = [
                (True, file_one, "Downloaded: one.mp3"),
                (True, file_two, "Downloaded: two.mp3"),
            ]

            urls = (
                "https://soundcloud.com/artist/one",
                "https://soundcloud.com/artist/two",
            )

            download_cmd = cast(Any, main.download)
            with mock.patch.object(main.URLValidator, "validate_url", return_value=(True, "SoundCloud")), \
                mock.patch.object(main, "_create_downloader", return_value=downloader), \
                mock.patch.object(click, "secho") as secho_mock:
                download_cmd.callback.__wrapped__(ctx, urls, None, True, False)

        self.assertEqual(downloader.download.call_count, 2)
        secho_mock.assert_any_call("Summary: 2 succeeded, 0 failed", fg="green", bold=True)

    def test_download_respects_config_continue_on_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            file_two = download_dir / "two.mp3"
            file_two.touch()

            cfg = Mock(download_dir=download_dir, open_music_app=False, default_playlist=None, continue_on_error=True)
            logger = Mock()
            ctx = mock.Mock()
            ctx.obj = {"config": cfg, "logger": logger}

            downloader = Mock()
            downloader.download.side_effect = [
                (False, None, "Temporary network error"),
                (True, file_two, "Downloaded: two.mp3"),
            ]

            urls = (
                "https://soundcloud.com/artist/one",
                "https://soundcloud.com/artist/two",
            )

            download_cmd = cast(Any, main.download)
            with mock.patch.object(main.URLValidator, "validate_url", return_value=(True, "SoundCloud")), \
                mock.patch.object(main, "_create_downloader", return_value=downloader), \
                mock.patch.object(click, "secho") as secho_mock:
                # CLI flag is False, but config.continue_on_error is True -> should continue
                download_cmd.callback.__wrapped__(ctx, urls, None, True, False)

        self.assertEqual(downloader.download.call_count, 2)
        secho_mock.assert_any_call("Summary: 1 succeeded, 1 failed", fg="yellow", bold=True)

    def test_batch_respects_config_continue_on_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_file = Path(tmpdir) / "urls.txt"
            batch_file.write_text("https://soundcloud.com/artist/one\nhttps://soundcloud.com/artist/two\n")

            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            file_two = download_dir / "two.mp3"
            file_two.touch()

            cfg = Mock(download_dir=download_dir, open_music_app=False, default_playlist=None, continue_on_error=True)
            logger = Mock()
            ctx = mock.Mock()
            ctx.obj = {"config": cfg, "logger": logger}

            downloader = Mock()
            downloader.download.side_effect = [
                (False, None, "Temporary error"),
                (True, file_two, "Downloaded: two.mp3"),
            ]

            batch_cmd = cast(Any, main.batch)
            with mock.patch.object(main.URLValidator, "validate_batch_file", return_value=(True, ["https://soundcloud.com/artist/one", "https://soundcloud.com/artist/two"], [])), \
                mock.patch.object(main, "_create_downloader", return_value=downloader), \
                mock.patch.object(apple_music, "AppleMusicManager"), \
                mock.patch.object(click, "secho") as secho_mock:
                # CLI flag False, config True
                batch_cmd.callback.__wrapped__(ctx, str(batch_file), None, False)

        self.assertEqual(downloader.download.call_count, 2)
        secho_mock.assert_any_call("Summary: 1 succeeded, 1 failed", fg="yellow", bold=True)

    def test_batch_shows_final_summary_with_success_and_failure_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_file = Path(tmpdir) / "urls.txt"
            batch_file.write_text("https://soundcloud.com/artist/one\nhttps://soundcloud.com/artist/two\n")

            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            file_path = download_dir / "track.mp3"
            file_path.touch()

            cfg = Mock(download_dir=download_dir, open_music_app=False, default_playlist=None)
            logger = Mock()
            ctx = mock.Mock()
            ctx.obj = {"config": cfg, "logger": logger}

            downloader = Mock()
            downloader.download.side_effect = [
                (True, file_path, "Downloaded: track.mp3"),
                (False, None, "The URL is invalid or not supported. Please check the link and try again."),
            ]

            batch_cmd = cast(Any, main.batch)
            with mock.patch.object(main.URLValidator, "validate_batch_file", return_value=(True, ["https://soundcloud.com/artist/one", "https://soundcloud.com/artist/two"], [])), \
                mock.patch.object(main, "_create_downloader", return_value=downloader), \
                mock.patch.object(apple_music, "AppleMusicManager"), \
                mock.patch.object(click, "secho") as secho_mock:
                batch_cmd.callback.__wrapped__(ctx, str(batch_file), None, True)

        secho_mock.assert_any_call("Summary: 1 succeeded, 1 failed", fg="yellow", bold=True)


if __name__ == "__main__":
    unittest.main()
