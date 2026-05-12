"""
Metadata embedding utilities for downloaded audio files.
"""

from __future__ import annotations

import base64
from datetime import datetime
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from mutagen.easyid3 import EasyID3, EasyID3KeyError
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TCON, TDRC, TPE2, TSSE, TXXX

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Writes SoundCloud/yt-dlp metadata into local audio files."""

    USER_AGENT = "sc2am/0.1"
    FALLBACK_COVER_ART_PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5f6WcAAAAASUVORK5CYII="
    )

    def write_to_file(self, file_path: Path, track_info: Dict[str, Any]) -> Tuple[bool, str]:
        """Write text tags and artwork to an MP3 file."""
        if not file_path.exists():
            return False, f"File not found: {file_path}"

        if file_path.suffix.lower() != ".mp3":
            return False, f"Unsupported audio format: {file_path.suffix}"

        try:
            self._write_text_tags(file_path, track_info)
            self._write_cover_art(file_path, track_info)
            return True, "Metadata embedded"
        except Exception as exc:
            logger.error(f"Failed to embed metadata: {exc}")
            return False, str(exc)

    def _write_text_tags(self, file_path: Path, track_info: Dict[str, Any]) -> None:
        tags = self._extract_tags(track_info)

        try:
            audio = EasyID3(str(file_path))
        except Exception:
            audio = EasyID3()
            audio.save(str(file_path))
            audio = EasyID3(str(file_path))

        for key, value in tags.items():
            if value:
                try:
                    audio[key] = [value]
                except EasyID3KeyError:
                    logger.debug(f"Skipping unsupported EasyID3 field: {key}")

        audio.save()

        # Write additional ID3 frames not covered by EasyID3.
        try:
            id3 = ID3(str(file_path))
        except ID3NoHeaderError:
            id3 = ID3()

        album_artist = tags.get("albumartist")
        if album_artist:
            id3.delall("TPE2")
            id3.add(TPE2(encoding=3, text=[album_artist]))

        self._write_id3_text_frame(id3, "TALB", TALB, tags.get("album"))
        self._write_id3_text_frame(id3, "TCON", TCON, tags.get("genre"))
        self._write_id3_text_frame(id3, "TDRC", TDRC, tags.get("date"))

        id3.delall("TSSE")
        id3.add(TSSE(encoding=3, text=["sc2am"]))

        source_url = self._first_available(track_info.get("webpage_url"), track_info.get("original_url"))
        if source_url:
            id3.delall("TXXX:SOURCE_URL")
            id3.add(TXXX(encoding=3, desc="SOURCE_URL", text=[source_url]))
        id3.save(str(file_path), v2_version=3)

    def _write_cover_art(self, file_path: Path, track_info: Dict[str, Any]) -> None:
        for thumbnail_url in self._cover_art_candidates(track_info):
            image_bytes, mime = self._download_image(thumbnail_url)
            if image_bytes:
                self._save_cover_art(file_path, image_bytes, mime)
                return

        fallback_bytes, fallback_mime = self._fallback_cover_art()
        self._save_cover_art(file_path, fallback_bytes, fallback_mime)

    def _extract_tags(self, track_info: Dict[str, Any]) -> Dict[str, str]:
        track_value = track_info.get("track")
        title = self._first_available(
            self._first_available(track_value) if not self._looks_like_track_number(track_value) else "",
            track_info.get("title"),
            "Unknown Title",
        )
        artist = self._first_available(
            track_info.get("artist"),
            track_info.get("creator"),
            track_info.get("uploader"),
            track_info.get("channel_name"),
            track_info.get("channel"),
            "Unknown Artist",
        )
        title = self._strip_artist_prefix(title, artist)
        album = self._first_available(
            track_info.get("album"),
            track_info.get("album_name"),
            track_info.get("release_title"),
            track_info.get("collection"),
            "SoundCloud",
        )
        album_artist = self._first_available(track_info.get("album_artist"), artist)
        genre = self._first_available(
            track_info.get("genre"),
            track_info.get("genre_name"),
            track_info.get("categories"),
            track_info.get("category"),
            "",
        )
        date = self._first_available(
            track_info.get("release_date"),
            track_info.get("upload_date"),
            track_info.get("release_timestamp"),
            track_info.get("timestamp"),
            track_info.get("release_year"),
            "",
        )
        track_number = self._first_available(
            self._stringify(track_info.get("track_number")),
            self._stringify(track_info.get("track")) if isinstance(track_info.get("track"), int) else "",
            "",
        )

        return {
            "title": title,
            "artist": artist,
            "album": album,
            "albumartist": album_artist,
            "genre": genre,
            "date": self._normalize_date_value(date),
            "tracknumber": str(track_number) if track_number else "",
        }

    @staticmethod
    def _download_image(url: str) -> Tuple[Optional[bytes], str]:
        try:
            response = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": MetadataWriter.USER_AGENT},
            )
            response.raise_for_status()
            image_bytes = response.content
            mime = MetadataWriter._detect_image_mime(image_bytes, response.headers.get("Content-Type", ""))
            if not image_bytes or not mime:
                return None, "image/jpeg"
            return image_bytes, mime
        except Exception as exc:
            logger.warning(f"Could not download artwork: {exc}")
            return None, "image/jpeg"

    @staticmethod
    def _first_available(*values: Any) -> str:
        for value in values:
            if value is None:
                continue
            string_value = str(value).strip()
            if string_value:
                return string_value
        return ""

    @staticmethod
    def _looks_like_track_number(value: Any) -> bool:
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            stripped = value.strip()
            return bool(stripped) and stripped.isdigit()
        return False

    @staticmethod
    def _strip_artist_prefix(title: str, artist: str) -> str:
        cleaned_title = title.strip()
        cleaned_artist = artist.strip()

        if not cleaned_title or not cleaned_artist:
            return cleaned_title

        separators = (" - ", " – ", " — ", " | ", ": ")
        normalized_title = cleaned_title.lower()
        normalized_artist = cleaned_artist.lower()

        if normalized_title == normalized_artist:
            return cleaned_title

        for separator in separators:
            prefix = f"{cleaned_artist}{separator}"
            if normalized_title.startswith(prefix.lower()):
                stripped_title = cleaned_title[len(prefix):].strip()
                if stripped_title:
                    return stripped_title

        return re.sub(r"\s+", " ", cleaned_title)

    @staticmethod
    def _normalize_date_value(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value).date().isoformat()
            except (OverflowError, OSError, ValueError):
                return str(value)

        text = str(value).strip()
        if not text:
            return ""

        if text.isdigit() and len(text) in {10, 13}:
            try:
                timestamp = int(text[:10])
                return datetime.fromtimestamp(timestamp).date().isoformat()
            except (OverflowError, OSError, ValueError):
                return text

        if re.fullmatch(r"\d{8}", text):
            return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"

        return text

    @staticmethod
    def _write_id3_text_frame(
        id3: ID3,
        frame_id: str,
        frame_cls: Any,
        value: Optional[str],
    ) -> None:
        if not value:
            return

        id3.delall(frame_id)
        id3.add(frame_cls(encoding=3, text=[value]))

    @staticmethod
    def _cover_art_candidates(track_info: Dict[str, Any]) -> list[str]:
        candidates = []

        def add_candidate(value: Any) -> None:
            url = MetadataWriter._extract_image_url(value)
            if url and url not in candidates:
                candidates.append(url)

        for key in (
            "thumbnail",
            "artwork_url",
            "cover_art",
            "cover_art_url",
            "cover_url",
            "image",
            "thumbnail_url",
            "album_art",
            "album_art_url",
        ):
            add_candidate(track_info.get(key))

        thumbnails = track_info.get("thumbnails")
        if isinstance(thumbnails, list):
            sorted_thumbnails = sorted(
                (item for item in thumbnails if isinstance(item, dict)),
                key=lambda item: MetadataWriter._thumbnail_area(item),
                reverse=True,
            )
            for thumbnail in sorted_thumbnails:
                add_candidate(thumbnail)

        return candidates

    @staticmethod
    def _extract_image_url(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            for key in ("url", "secure_url", "source", "src"):
                candidate = value.get(key)
                if candidate:
                    candidate_str = str(candidate).strip()
                    if candidate_str:
                        return candidate_str
        return ""

    @staticmethod
    def _thumbnail_area(thumbnail: Dict[str, Any]) -> int:
        width = thumbnail.get("width") or 0
        height = thumbnail.get("height") or 0
        try:
            return int(width) * int(height)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _detect_image_mime(image_bytes: bytes, content_type: str) -> Optional[str]:
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if image_bytes.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if len(image_bytes) >= 12 and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            return "image/webp"

        lowered = (content_type or "").lower()
        if "png" in lowered:
            return "image/png"
        if "jpeg" in lowered or "jpg" in lowered:
            return "image/jpeg"
        if "gif" in lowered:
            return "image/gif"
        if "webp" in lowered:
            return "image/webp"
        return None

    def _save_cover_art(self, file_path: Path, image_bytes: bytes, mime: str) -> None:
        if not image_bytes:
            return

        try:
            id3 = ID3(str(file_path))
        except ID3NoHeaderError:
            id3 = ID3()

        id3.delall("APIC")
        id3.add(
            APIC(
                encoding=3,
                mime=mime,
                type=3,
                desc="Cover",
                data=image_bytes,
            )
        )
        id3.save(str(file_path), v2_version=3)

    @classmethod
    def _fallback_cover_art(cls) -> Tuple[bytes, str]:
        return cls.FALLBACK_COVER_ART_PNG, "image/png"

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        return str(value)



