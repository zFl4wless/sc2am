import unittest
from pathlib import Path
from unittest.mock import Mock

import click

from main import _exit_with_error
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

    def test_missing_music_file_returns_clear_error(self):
        success, message = AppleMusicManager.open_file_with_music(Path("/tmp/does-not-exist.mp3"))

        self.assertFalse(success)
        self.assertEqual(message, "The downloaded file was not found.")

    def test_missing_playlist_file_returns_clear_error(self):
        success, message = AppleMusicManager.add_to_playlist(
            Path("/tmp/does-not-exist.mp3"),
            "My Playlist",
        )

        self.assertFalse(success)
        self.assertEqual(message, "The downloaded file was not found.")

    def test_exit_helper_raises_click_exception(self):
        logger = Mock()

        with self.assertRaises(click.ClickException) as ctx:
            _exit_with_error(logger, "Something went wrong.")

        self.assertEqual(str(ctx.exception), "Something went wrong.")
        logger.error.assert_called_once_with("Something went wrong.")


if __name__ == "__main__":
    unittest.main()
