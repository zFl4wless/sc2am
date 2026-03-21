"""
Metadata embedding utilities for downloaded audio files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from mutagen.easyid3 import EasyID3, EasyID3KeyError
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TPE2, TSSE, TXXX

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Writes SoundCloud/yt-dlp metadata into local audio files."""

    USER_AGENT = "sc2am/0.1"

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

        id3.delall("TSSE")
        id3.add(TSSE(encoding=3, text=["sc2am"]))

        source_url = self._first_available(track_info.get("webpage_url"), track_info.get("original_url"))
        if source_url:
            id3.delall("TXXX:SOURCE_URL")
            id3.add(TXXX(encoding=3, desc="SOURCE_URL", text=[source_url]))
        id3.save(str(file_path), v2_version=3)

    def _write_cover_art(self, file_path: Path, track_info: Dict[str, Any]) -> None:
        thumbnail_url = self._first_available(
            track_info.get("thumbnail"),
            track_info.get("artwork_url"),
            track_info.get("thumbnails", [{}])[0].get("url") if track_info.get("thumbnails") else None,
        )
        if not thumbnail_url:
            return

        image_bytes, mime = self._download_image(thumbnail_url)
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

    def _extract_tags(self, track_info: Dict[str, Any]) -> Dict[str, str]:
        title = self._first_available(track_info.get("track"), track_info.get("title"), "Unknown Title")
        artist = self._first_available(
            track_info.get("artist"),
            track_info.get("uploader"),
            track_info.get("creator"),
            "Unknown Artist",
        )
        album = self._first_available(track_info.get("album"), "SoundCloud")
        album_artist = self._first_available(track_info.get("album_artist"), artist)
        genre = self._first_available(track_info.get("genre"), "")
        date = self._first_available(
            track_info.get("release_date"),
            track_info.get("upload_date"),
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
            "date": str(date) if date else "",
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
            content_type = response.headers.get("Content-Type", "").lower()
            if "png" in content_type:
                mime = "image/png"
            else:
                mime = "image/jpeg"
            return response.content, mime
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
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        return str(value)



