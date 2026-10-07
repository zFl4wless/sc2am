import unittest
import tempfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from PIL import Image
from mutagen.id3 import ID3

from sc2am.metadata import MetadataWriter


def make_image_bytes(image_format="PNG", color=(25, 80, 160, 255), size=(24, 24)):
    mode = "RGBA" if image_format in {"PNG", "WEBP", "GIF"} else "RGB"
    image = Image.new(mode, size, color[:4] if mode == "RGBA" else color[:3])
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


class MetadataMappingTests(unittest.TestCase):
    def setUp(self):
        self.writer = MetadataWriter()

    @staticmethod
    def _create_mp3(file_path):
        fixture_path = Path(__file__).parent / "fixtures" / "silent-track.mp3"
        file_path.write_bytes(fixture_path.read_bytes())

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

    def test_normalize_track_info_flattens_raw_soundcloud_metadata(self):
        normalized = self.writer._normalize_track_info(
            {
                "track": {"name": "  Synthwave Collective - Night Drive  "},
                "artist": {"display_name": "  Synthwave Collective  "},
                "album": {"title": " Midnight Sessions "},
                "genre": [" Synthwave ", " Electronic "],
                "upload_date": " 20240510 ",
                "track_number": " 4/12 ",
                "thumbnails": [
                    {"url": " https://example.com/cover.jpg ", "width": "1024", "height": "1024"}
                ],
            }
        )

        self.assertEqual(normalized["track"], "Synthwave Collective - Night Drive")
        self.assertEqual(normalized["artist"], "Synthwave Collective")
        self.assertEqual(normalized["album"], "Midnight Sessions")
        self.assertEqual(normalized["genre"], "Synthwave, Electronic")
        self.assertEqual(normalized["upload_date"], "2024-05-10")
        self.assertEqual(normalized["track_number"], "4")
        self.assertEqual(normalized["thumbnails"][0]["url"], "https://example.com/cover.jpg")
        self.assertEqual(normalized["thumbnails"][0]["width"], 1024)
        self.assertEqual(normalized["thumbnails"][0]["height"], 1024)

    def test_write_to_file_uses_normalized_metadata_before_tagging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            self._create_mp3(file_path)

            track_info = {
                "track": {"name": "  Synthwave Collective - Night Drive  "},
                "artist": {"display_name": "  Synthwave Collective  "},
                "album": {"title": " Midnight Sessions "},
                "genre": [" Synthwave ", " Electronic "],
                "release_date": " 20240510 ",
            }

            with mock.patch.object(self.writer, "_write_cover_art", return_value=None):
                success, message = self.writer.write_to_file(file_path, track_info)

            self.assertTrue(success, message)

            id3 = ID3(str(file_path))
            self.assertEqual(id3.getall("TIT2")[0].text[0], "Night Drive")
            self.assertEqual(id3.getall("TPE1")[0].text[0], "Synthwave Collective")
            self.assertEqual(id3.getall("TALB")[0].text[0], "Midnight Sessions")
            self.assertEqual(id3.getall("TCON")[0].text[0], "Synthwave, Electronic")
            self.assertEqual(str(id3.getall("TDRC")[0].text[0]), "2024-05-10")

    def test_write_to_file_persists_album_genre_and_date_frames(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            self._create_mp3(file_path)

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
            self._create_mp3(file_path)

            with mock.patch.object(
                self.writer,
                "_download_image",
                return_value=(None, "image/jpeg"),
            ) as download_mock:
                with mock.patch.object(
                    MetadataWriter,
                    "_fallback_cover_art",
                    return_value=(MetadataWriter.FALLBACK_COVER_ART_PNG, "image/png"),
                ) as fallback_mock:
                    artwork_status = self.writer._write_cover_art(file_path, {})

            download_mock.assert_not_called()
            fallback_mock.assert_called_once()

            id3 = ID3(str(file_path))
            apic = id3.getall("APIC")[0]
            self.assertEqual(artwork_status, "fallback")
            self.assertEqual(apic.mime, "image/jpeg")
            with Image.open(BytesIO(apic.data)) as image:
                self.assertEqual(image.format, "JPEG")

    def test_write_cover_art_falls_back_from_failed_primary_thumbnail_to_secondary_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            self._create_mp3(file_path)

            large_image_bytes = make_image_bytes("JPEG", color=(20, 90, 150, 255))

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
                    return large_image_bytes, "image/jpeg"
                self.fail(f"Unexpected thumbnail URL: {url}")

            with mock.patch.object(
                self.writer, "_download_image", side_effect=download_side_effect
            ):
                with mock.patch.object(
                    self.writer, "_save_cover_art", wraps=self.writer._save_cover_art
                ) as save_mock:
                    self.writer._write_cover_art(file_path, track_info)

            self.assertEqual(save_mock.call_count, 1)
            saved_args = save_mock.call_args.args
            self.assertEqual(saved_args[1], large_image_bytes)
            self.assertEqual(saved_args[2], "image/jpeg")

    def test_download_image_streams_and_normalizes_valid_image_even_with_wrong_content_type(self):
        png_bytes = make_image_bytes("PNG")
        response = mock.Mock()
        response.headers = {
            "Content-Length": str(len(png_bytes)),
            "Content-Type": "text/plain",
        }
        response.iter_content.return_value = iter([png_bytes])

        with mock.patch("sc2am.metadata.requests.get", return_value=response) as get_mock:
            image_bytes, mime = self.writer._download_image("https://example.com/artwork")

        get_mock.assert_called_once_with(
            "https://example.com/artwork",
            stream=True,
            timeout=(5, 2),
            headers={"User-Agent": MetadataWriter.USER_AGENT},
        )
        response.close.assert_called_once()
        self.assertEqual(mime, "image/jpeg")
        with Image.open(BytesIO(image_bytes)) as image:
            self.assertEqual(image.format, "JPEG")

    def test_download_image_rejects_invalid_bytes_despite_image_content_type(self):
        response = mock.Mock()
        response.headers = {"Content-Type": "image/jpeg"}
        response.iter_content.return_value = iter([b"not actually an image"])

        with mock.patch("sc2am.metadata.requests.get", return_value=response):
            image_bytes, _ = self.writer._download_image("https://example.com/bad-image")

        self.assertIsNone(image_bytes)
        response.close.assert_called_once()

    def test_download_image_rejects_truncated_image(self):
        png_bytes = make_image_bytes("PNG")[:-10]
        response = mock.Mock()
        response.headers = {"Content-Type": "image/png"}
        response.iter_content.return_value = iter([png_bytes])

        with mock.patch("sc2am.metadata.requests.get", return_value=response):
            image_bytes, _ = self.writer._download_image("https://example.com/truncated-image")

        self.assertIsNone(image_bytes)
        response.close.assert_called_once()

    def test_download_image_rejects_oversized_content_length_before_reading(self):
        response = mock.Mock()
        response.headers = {"Content-Length": str(MetadataWriter.ARTWORK_MAX_BYTES + 1)}

        with mock.patch("sc2am.metadata.requests.get", return_value=response):
            image_bytes, _ = self.writer._download_image("https://example.com/large-image")

        self.assertIsNone(image_bytes)
        response.iter_content.assert_not_called()
        response.close.assert_called_once()

    def test_download_image_rejects_oversized_stream_without_content_length(self):
        response = mock.Mock()
        response.headers = {}
        response.iter_content.return_value = iter([b"x" * (MetadataWriter.ARTWORK_MAX_BYTES + 1)])

        with mock.patch("sc2am.metadata.requests.get", return_value=response):
            image_bytes, _ = self.writer._download_image("https://example.com/chunked-image")

        self.assertIsNone(image_bytes)
        response.close.assert_called_once()

    def test_normalize_image_rejects_pixel_dimensions_over_limit(self):
        image_bytes = make_image_bytes(size=(8, 8))

        with mock.patch.object(MetadataWriter, "ARTWORK_MAX_PIXELS", 63):
            normalized = self.writer._normalize_image(image_bytes)

        self.assertIsNone(normalized)

    def test_download_image_enforces_total_time_limit(self):
        png_bytes = make_image_bytes("PNG")
        response = mock.Mock()
        response.headers = {}
        clock = [0.0]

        def delayed_chunks(chunk_size):
            yield png_bytes
            clock[0] = MetadataWriter.ARTWORK_TOTAL_TIMEOUT_SECONDS + 1

        response.iter_content.side_effect = delayed_chunks

        with mock.patch("sc2am.metadata.requests.get", return_value=response):
            with mock.patch("sc2am.metadata.time.monotonic", side_effect=lambda: clock[0]):
                image_bytes, _ = self.writer._download_image("https://example.com/slow-image")

        self.assertIsNone(image_bytes)
        response.close.assert_called_once()

    def test_download_image_total_time_limit_includes_image_decoding(self):
        response = mock.Mock()
        response.headers = {}
        response.iter_content.return_value = iter([b"image bytes"])
        clock = [0.0]

        def slow_normalize(image_bytes):
            clock[0] = MetadataWriter.ARTWORK_TOTAL_TIMEOUT_SECONDS + 1
            return b"normalized image"

        with mock.patch("sc2am.metadata.requests.get", return_value=response):
            with mock.patch("sc2am.metadata.time.monotonic", side_effect=lambda: clock[0]):
                with mock.patch.object(
                    MetadataWriter, "_normalize_image", side_effect=slow_normalize
                ):
                    image_bytes, _ = self.writer._download_image("https://example.com/slow-decode")

        self.assertIsNone(image_bytes)
        response.close.assert_called_once()

    def test_write_to_file_reports_when_fallback_artwork_was_used(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            self._create_mp3(file_path)

            with mock.patch.object(self.writer, "_write_cover_art", return_value="fallback"):
                success, message = self.writer.write_to_file(file_path, {"title": "Fixture"})

        self.assertTrue(success)
        self.assertEqual(
            message,
            "Metadata embedded with fallback artwork; downloaded artwork unavailable",
        )

    def test_validated_download_artwork_is_embedded_as_jpeg_in_an_mp3_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            self._create_mp3(file_path)
            png_bytes = make_image_bytes("PNG")
            jpeg_bytes = self.writer._normalize_image(png_bytes)

            with mock.patch.object(
                self.writer,
                "_download_image",
                return_value=(jpeg_bytes, "image/jpeg"),
            ):
                artwork_status = self.writer._write_cover_art(
                    file_path, {"thumbnail": "https://example.com/cover"}
                )

            self.assertEqual(artwork_status, "verified")
            apic = ID3(str(file_path)).getall("APIC")[0]
            self.assertEqual(apic.mime, "image/jpeg")
            with Image.open(BytesIO(apic.data)) as image:
                self.assertEqual(image.format, "JPEG")

    def test_save_cover_art_verifies_the_written_artwork_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            self._create_mp3(file_path)

            image_bytes = MetadataWriter.FALLBACK_COVER_ART_PNG
            success = self.writer._save_cover_art(file_path, image_bytes, "image/png")

            self.assertTrue(success)

            id3 = ID3(str(file_path))
            apic = id3.getall("APIC")[0]
            self.assertEqual(apic.data, image_bytes)
            self.assertEqual(apic.mime, "image/png")

    def test_write_cover_art_retries_when_saved_artwork_cannot_be_verified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "track.mp3"
            self._create_mp3(file_path)

            downloaded_image = make_image_bytes("JPEG")

            track_info = {
                "thumbnail": "https://example.com/broken.jpg",
                "thumbnails": [
                    {"url": "https://example.com/large.jpg", "width": 1280, "height": 720},
                ],
            }

            with mock.patch.object(
                self.writer,
                "_download_image",
                side_effect=[
                    (downloaded_image, "image/jpeg"),
                    (downloaded_image, "image/jpeg"),
                ],
            ):
                with mock.patch.object(
                    MetadataWriter,
                    "_verify_cover_art",
                    side_effect=[False, True],
                ) as verify_mock:
                    with mock.patch.object(
                        MetadataWriter,
                        "_fallback_cover_art",
                        return_value=(MetadataWriter.FALLBACK_COVER_ART_PNG, "image/png"),
                    ) as fallback_mock:
                        verified = self.writer._write_cover_art(file_path, track_info)

            self.assertTrue(verified)
            self.assertEqual(verify_mock.call_count, 2)
            fallback_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
