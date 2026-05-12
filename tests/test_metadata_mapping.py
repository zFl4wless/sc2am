import unittest
import tempfile
from pathlib import Path
from unittest import mock

from mutagen.id3 import ID3

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

    def test_extract_tags_preserves_album_genre_and_release_date_from_alternate_fields(self):
        tags = self.writer._extract_tags(
            {
                "title": "Night Drive",
                "artist": "Synthwave Collective",
                "album_name": "Midnight Sessions",
                "genre_name": "Synthwave",
                "release_date": "20240510",
            }
        )

        self.assertEqual(tags["album"], "Midnight Sessions")
        self.assertEqual(tags["genre"], "Synthwave")
        self.assertEqual(tags["date"], "2024-05-10")

    def test_write_to_file_persists_album_genre_and_date_frames(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()
            ID3().save(str(file_path), v2_version=3)

            track_info = {
                "title": "Night Drive",
                "artist": "Synthwave Collective",
                "album": "Midnight Sessions",
                "genre": "Synthwave",
                "upload_date": "20240510",
            }

            with mock.patch.object(self.writer, "_write_cover_art", return_value=None):
                success, message = self.writer.write_to_file(file_path, track_info)

            self.assertTrue(success, message)

            id3 = ID3(str(file_path))
            self.assertEqual(id3.getall("TALB")[0].text[0], "Midnight Sessions")
            self.assertEqual(id3.getall("TCON")[0].text[0], "Synthwave")
            self.assertEqual(str(id3.getall("TDRC")[0].text[0]), "2024-05-10")

    def test_cover_art_candidates_prefer_largest_thumbnail_when_direct_fields_missing(self):
        candidates = self.writer._cover_art_candidates(
            {
                "thumbnails": [
                    {"url": "https://example.com/small.jpg", "width": 64, "height": 64},
                    {"url": "https://example.com/large.jpg", "width": 1280, "height": 720},
                    {"url": "https://example.com/medium.jpg", "width": 320, "height": 320},
                ]
            }
        )

        self.assertEqual(
            candidates,
            [
                "https://example.com/large.jpg",
                "https://example.com/medium.jpg",
                "https://example.com/small.jpg",
            ],
        )

    def test_write_cover_art_uses_fallback_image_when_no_artwork_is_usable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()
            ID3().save(str(file_path), v2_version=3)

            with mock.patch.object(
                self.writer,
                "_download_image",
                return_value=(None, "image/jpeg"),
            ) as download_mock:
                with mock.patch.object(
                    MetadataWriter,
                    "_fallback_cover_art",
                    return_value=(b"fallback-cover", "image/png"),
                ) as fallback_mock:
                    self.writer._write_cover_art(file_path, {})

            download_mock.assert_not_called()
            fallback_mock.assert_called_once()

            id3 = ID3(str(file_path))
            apic = id3.getall("APIC")[0]
            self.assertEqual(apic.data, b"fallback-cover")
            self.assertEqual(apic.mime, "image/png")

    def test_write_cover_art_falls_back_from_failed_primary_thumbnail_to_secondary_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            file_path.touch()
            ID3().save(str(file_path), v2_version=3)

            track_info = {
                "thumbnail": "https://example.com/broken.jpg",
                "thumbnails": [
                    {"url": "https://example.com/small.jpg", "width": 64, "height": 64},
                    {"url": "https://example.com/large.jpg", "width": 1280, "height": 720},
                ],
            }

            def download_side_effect(url):
                if url == "https://example.com/broken.jpg":
                    return None, "image/jpeg"
                if url == "https://example.com/large.jpg":
                    return b"large-image-bytes", "image/jpeg"
                self.fail(f"Unexpected thumbnail URL: {url}")

            with mock.patch.object(self.writer, "_download_image", side_effect=download_side_effect):
                with mock.patch.object(self.writer, "_save_cover_art", wraps=self.writer._save_cover_art) as save_mock:
                    self.writer._write_cover_art(file_path, track_info)

            self.assertEqual(save_mock.call_count, 1)
            saved_args = save_mock.call_args.args
            self.assertEqual(saved_args[1], b"large-image-bytes")
            self.assertEqual(saved_args[2], "image/jpeg")


if __name__ == "__main__":
    unittest.main()

