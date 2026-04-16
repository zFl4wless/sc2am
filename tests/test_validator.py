import unittest

from sc2am.validator import URLValidator


class URLValidatorTests(unittest.TestCase):
    def test_accepts_soundcloud_track_without_explicit_scheme(self):
        is_valid, message = URLValidator.validate_url("soundcloud.com/artist/track")

        self.assertTrue(is_valid)
        self.assertEqual(message, "SoundCloud")

    def test_rejects_soundcloud_urls_with_invalid_path_depth(self):
        is_valid, message = URLValidator.validate_url("https://soundcloud.com/artist/track/remix")

        self.assertFalse(is_valid)
        self.assertEqual(
            message,
            URLValidator.SOUNDCLOUD_TRACK_HELP,
        )

    def test_rejects_urls_without_domain(self):
        is_valid, message = URLValidator.validate_url("https://")

        self.assertFalse(is_valid)
        self.assertEqual(message, "The URL is missing a domain name.")

    def test_rejects_non_string_values(self):
        is_valid, message = URLValidator.validate_url(None)

        self.assertFalse(is_valid)
        self.assertEqual(message, "Please provide a valid URL.")


if __name__ == "__main__":
    unittest.main()
