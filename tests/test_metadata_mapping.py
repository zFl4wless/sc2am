import unittest

from sc2am.metadata import MetadataWriter


class MetadataMappingTests(unittest.TestCase):
    def setUp(self):
        self.writer = MetadataWriter()

    def test_extract_tags_strips_artist_prefix_from_title(self):
        tags = self.writer._extract_tags(
            {
                "track": "Synthwave Collective - Night Drive",
                "artist": "Synthwave Collective",
                "album": "Midnight Sessions",
            }
        )

        self.assertEqual(tags["title"], "Night Drive")
        self.assertEqual(tags["artist"], "Synthwave Collective")
        self.assertEqual(tags["albumartist"], "Synthwave Collective")
        self.assertEqual(tags["album"], "Midnight Sessions")

    def test_extract_tags_uses_title_when_track_is_numeric_and_creator_for_artist(self):
        tags = self.writer._extract_tags(
            {
                "track": 4,
                "title": "Morning Light",
                "creator": "DJ Echo",
            }
        )

        self.assertEqual(tags["title"], "Morning Light")
        self.assertEqual(tags["artist"], "DJ Echo")
        self.assertEqual(tags["albumartist"], "DJ Echo")

    def test_extract_tags_falls_back_to_uploader_and_unknown_defaults(self):
        tags = self.writer._extract_tags(
            {
                "title": "Lo-Fi Study Session",
                "uploader": "Chill Beats Radio",
            }
        )

        self.assertEqual(tags["title"], "Lo-Fi Study Session")
        self.assertEqual(tags["artist"], "Chill Beats Radio")
        self.assertEqual(tags["albumartist"], "Chill Beats Radio")
        self.assertEqual(tags["genre"], "")
        self.assertEqual(tags["date"], "")
        self.assertEqual(tags["tracknumber"], "")


if __name__ == "__main__":
    unittest.main()

