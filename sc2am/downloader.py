"""
Core downloader module for sc2am.
Handles downloading audio from various platforms using yt-dlp.
"""

import logging
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import shutil

from .metadata import MetadataWriter
from .logger import DIAGNOSTIC_HINT
from .validator import URLValidator

logger = logging.getLogger(__name__)


class Downloader:
    """Downloads audio tracks from supported platforms."""

    _MAX_RETRIES = 3
    _RETRY_DELAY_SECONDS = 1.0

    _INVALID_URL_PATTERNS = (
        "unsupported url",
        "invalid url",
        "no suitable extractors",
        "no extractors found",
        "not a valid url",
    )
    _TEMPORARY_NETWORK_PATTERNS = (
        "timed out",
        "timeout",
        "temporary failure",
        "name or service not known",
        "connection refused",
        "connection reset",
        "network is unreachable",
        "unable to download webpage",
        "http error 5",
        "bad gateway",
        "gateway timeout",
        "service unavailable",
    )
    _ACCESS_PATTERNS = (
        "http error 401",
        "http error 403",
        "forbidden",
        "access denied",
        "private",
    )
    _NOT_FOUND_PATTERNS = (
        "http error 404",
        "not found",
        "deleted",
        "removed",
    )

    def __init__(self, download_dir: Path):
        """
        Initialize downloader.

        Args:
            download_dir: Directory where files will be downloaded
        """
        self.download_dir = Path(download_dir)
        self.metadata_writer = MetadataWriter()
        self._check_dependencies()

    @staticmethod
    def _check_dependencies() -> None:
        """Check that yt-dlp and the FFmpeg tools required for MP3 extraction exist."""
        for executable, install_command in (
            ("yt-dlp", "pip install yt-dlp"),
            ("ffmpeg", "brew install ffmpeg"),
            ("ffprobe", "brew install ffmpeg"),
        ):
            executable_path = shutil.which(executable)
            if not executable_path:
                raise RuntimeError(
                    f"{executable} is not installed. Install it with '{install_command}' and try again."
                )
            logger.debug(f"{executable} found at: {executable_path}")

    @classmethod
    def _is_retryable_error(cls, stderr: str) -> bool:
        lowered = (stderr or "").lower()
        return any(pattern in lowered for pattern in cls._TEMPORARY_NETWORK_PATTERNS)

    @classmethod
    def _sleep_before_retry(cls, attempt: int) -> None:
        time.sleep(cls._RETRY_DELAY_SECONDS * attempt)

    def download(self, url: str) -> Tuple[bool, Optional[Path], str]:
        """
        Download audio from URL.

        Args:
            url: URL to download from

        Returns:
            Tuple of (success, file_path, message)
        """
        valid, message = URLValidator.validate_url(url)
        if not valid:
            return False, None, message

        info_ok, info, info_msg = self.get_track_info(url)
        if not info_ok or info is None:
            return False, None, info_msg
        track_info = info

        # Download only after extraction has confirmed a single track.
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            message = (
                f"Could not create download directory '{self.download_dir}'. "
                "Check the path and permissions."
            )
            logger.exception("Could not prepare download directory: %s", self.download_dir)
            return False, None, message

        # yt-dlp command
        output_template = str(self.download_dir.resolve() / "%(title)s [%(id)s].%(ext)s")

        cmd = [
            "yt-dlp",
            "--ignore-config",
            "--no-playlist",
            "--format",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "192",
            "--output",
            output_template,
            "--no-overwrites",
            "--print",
            "after_move:%(filepath)j",
            "--quiet",
            url,
        ]

        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                logger.debug(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300  # 5 minutes timeout
                )

                if result.returncode != 0:
                    logger.error(
                        "yt-dlp download exited with %s: %s", result.returncode, result.stderr
                    )
                    error_msg = self._classify_download_error(result.stderr)
                    if attempt < self._MAX_RETRIES and self._is_retryable_error(result.stderr):
                        logger.warning(
                            f"Temporary download failure on attempt {attempt}/{self._MAX_RETRIES}: {error_msg}"
                        )
                        self._sleep_before_retry(attempt)
                        continue

                    logger.error(f"Download failed: {error_msg}")
                    return False, None, error_msg

                downloaded_file = self._resolve_downloaded_file(result.stdout)
                if downloaded_file is None:
                    if attempt < self._MAX_RETRIES:
                        logger.warning(
                            f"The download finished without a verified MP3 file on attempt {attempt}/{self._MAX_RETRIES}; retrying."
                        )
                        self._sleep_before_retry(attempt)
                        continue
                    return (
                        False,
                        None,
                        "The downloaded MP3 file could not be verified. Please try again.",
                    )

                metadata_message = ""
                if track_info:
                    meta_ok, meta_msg = self.metadata_writer.write_to_file(
                        downloaded_file, track_info
                    )
                    if meta_ok:
                        metadata_message = " (metadata embedded)"
                        if "fallback artwork" in meta_msg.lower():
                            metadata_message = " (metadata embedded; fallback artwork used)"
                        elif "no artwork could be saved" in meta_msg.lower():
                            metadata_message = " (metadata embedded; artwork unavailable)"
                    else:
                        metadata_message = " (metadata could not be added)"
                        logger.warning(f"Metadata tagging issue: {meta_msg}")

                logger.info(f"Successfully downloaded: {downloaded_file.name}")
                return (
                    True,
                    downloaded_file,
                    f"Downloaded: {downloaded_file.name}{metadata_message}",
                )

            except subprocess.TimeoutExpired:
                if attempt < self._MAX_RETRIES:
                    logger.warning(
                        f"The download timed out on attempt {attempt}/{self._MAX_RETRIES}; retrying."
                    )
                    self._sleep_before_retry(attempt)
                    continue

                message = "The download timed out. Please try again later."
                logger.error(message)
                return False, None, message
            except Exception:
                message = f"The download failed unexpectedly. {DIAGNOSTIC_HINT}"
                logger.exception("Unexpected download error")
                return False, None, message

        return False, None, f"The download failed after {self._MAX_RETRIES} attempts."

    @classmethod
    def _classify_download_error(cls, stderr: str) -> str:
        """Convert yt-dlp failures into user-friendly messages."""
        error_text = (stderr or "").strip()
        lowered = error_text.lower()

        if not error_text:
            return "The download failed. Please try again."

        if any(pattern in lowered for pattern in cls._INVALID_URL_PATTERNS):
            return "The URL is invalid or not supported. Please check the link and try again."

        if any(pattern in lowered for pattern in cls._ACCESS_PATTERNS):
            return "The track is private or unavailable. Please use a public SoundCloud track URL."

        if any(pattern in lowered for pattern in cls._NOT_FOUND_PATTERNS):
            return (
                "The track could not be found. It may have been removed or the link may be wrong."
            )

        if any(pattern in lowered for pattern in cls._TEMPORARY_NETWORK_PATTERNS):
            return "A temporary network error occurred. Please try again."

        return f"The download failed unexpectedly. {DIAGNOSTIC_HINT}"

    def _resolve_downloaded_file(self, stdout: str) -> Optional[Path]:
        """Accept only the single final MP3 path reported by this yt-dlp process."""
        try:
            # JSON preserves whitespace/newlines in filenames and rejects ambiguous output.
            filepath = json.loads(stdout)
            if not isinstance(filepath, str) or not filepath:
                return None
            candidate = Path(filepath)
            if (
                not candidate.is_absolute()
                or candidate.suffix.lower() != ".mp3"
                or candidate.is_symlink()
                or not candidate.is_file()
            ):
                return None
            resolved = candidate.resolve()
            if resolved.parent != self.download_dir.resolve():
                return None
            return candidate
        except (ValueError, OSError, RuntimeError):
            return None

    @staticmethod
    def get_track_info(url: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Get track information without downloading.

        Args:
            url: URL to get info from

        Returns:
            Tuple of (success, info_dict, message)
        """
        valid, message = URLValidator.validate_url(url)
        if not valid:
            return False, None, message

        cmd = [
            "yt-dlp",
            "--ignore-config",
            "--dump-single-json",
            "--flat-playlist",
            "--playlist-end",
            "1",
            "--no-warnings",
            url,
        ]

        for attempt in range(1, Downloader._MAX_RETRIES + 1):
            try:
                logger.debug("Running track-info command: %s", " ".join(cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    logger.error(
                        "yt-dlp track-info exited with %s: %s", result.returncode, result.stderr
                    )
                    error_msg = Downloader._classify_download_error(result.stderr)
                    if attempt < Downloader._MAX_RETRIES and Downloader._is_retryable_error(
                        result.stderr
                    ):
                        logger.warning(
                            f"Temporary track-info failure on attempt {attempt}/{Downloader._MAX_RETRIES}: {error_msg}"
                        )
                        Downloader._sleep_before_retry(attempt)
                        continue
                    return False, None, f"Could not fetch track info: {error_msg}"

                info = json.loads(result.stdout)
                if (
                    not isinstance(info, dict)
                    or info.get("_type", "video") != "video"
                    or "entries" in info
                ):
                    return False, None, URLValidator.SOUNDCLOUD_TRACK_HELP
                return True, info, "Info fetched successfully"

            except json.JSONDecodeError:
                if attempt < Downloader._MAX_RETRIES:
                    logger.warning(
                        f"Could not parse track information on attempt {attempt}/{Downloader._MAX_RETRIES}; retrying."
                    )
                    Downloader._sleep_before_retry(attempt)
                    continue
                logger.exception("Could not parse track information from yt-dlp")
                return (
                    False,
                    None,
                    f"Could not read track information from yt-dlp. {DIAGNOSTIC_HINT}",
                )
            except Exception:
                logger.exception("Error fetching track info")
                return (
                    False,
                    None,
                    f"Could not fetch track information. {DIAGNOSTIC_HINT}",
                )

        return (
            False,
            None,
            f"Could not fetch track information after {Downloader._MAX_RETRIES} attempts.",
        )
