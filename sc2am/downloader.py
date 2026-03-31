"""
Core downloader module for sc2am.
Handles downloading audio from various platforms using yt-dlp.
"""

import logging
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import shutil

from .metadata import MetadataWriter

logger = logging.getLogger(__name__)


class Downloader:
    """Downloads audio tracks from supported platforms."""

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
        """Check if yt-dlp is installed."""
        yt_dlp_path = shutil.which('yt-dlp')
        if not yt_dlp_path:
            raise RuntimeError(
                "yt-dlp is not installed. Install it with: pip install yt-dlp"
            )
        logger.debug(f"yt-dlp found at: {yt_dlp_path}")

    def download(self, url: str) -> Tuple[bool, Optional[Path], str]:
        """
        Download audio from URL.
        
        Args:
            url: URL to download from
            
        Returns:
            Tuple of (success, file_path, message)
        """
        # Create download directory if needed
        self.download_dir.mkdir(parents=True, exist_ok=True)

        track_info: Optional[Dict[str, Any]] = None
        info_ok, info, info_msg = self.get_track_info(url)
        if info_ok and info is not None:
            track_info = info
        else:
            logger.warning(f"Could not fetch track metadata before download: {info_msg}")
        
        # yt-dlp command
        output_template = str(self.download_dir / "%(title)s.%(ext)s")
        
        cmd = [
            'yt-dlp',
            '--format', 'bestaudio/best',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '192',
            '--output', output_template,
            '--print', 'after_move:filepath',
            '--quiet',
            url
        ]
        
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                error_msg = self._classify_download_error(result.stderr)
                logger.error(f"Download failed: {error_msg}")
                return False, None, error_msg

            downloaded_file = self._resolve_downloaded_file(result.stdout)
            if downloaded_file is None:
                return False, None, "No MP3 file found after download"

            metadata_message = ""
            if track_info:
                meta_ok, meta_msg = self.metadata_writer.write_to_file(downloaded_file, track_info)
                if meta_ok:
                    metadata_message = " (metadata embedded)"
                else:
                    metadata_message = f" (metadata skipped: {meta_msg})"
                    logger.warning(f"Metadata tagging issue: {meta_msg}")

            logger.info(f"Successfully downloaded: {downloaded_file.name}")
            return True, downloaded_file, f"Downloaded: {downloaded_file.name}{metadata_message}"
        
        except subprocess.TimeoutExpired:
            message = "Download timed out after 5 minutes. Please try again later."
            logger.error(message)
            return False, None, message
        except Exception as e:
            message = f"Unexpected download error: {str(e)}"
            logger.error(message)
            return False, None, message

    @classmethod
    def _classify_download_error(cls, stderr: str) -> str:
        """Convert yt-dlp failures into user-friendly messages."""
        error_text = (stderr or "").strip()
        lowered = error_text.lower()

        if not error_text:
            return "Download failed: yt-dlp returned an unknown error"

        if any(pattern in lowered for pattern in cls._INVALID_URL_PATTERNS):
            return f"Invalid or unsupported URL: {error_text}"

        if any(pattern in lowered for pattern in cls._ACCESS_PATTERNS):
            return f"Access denied or private track: {error_text}"

        if any(pattern in lowered for pattern in cls._NOT_FOUND_PATTERNS):
            return f"Track not found or removed: {error_text}"

        if any(pattern in lowered for pattern in cls._TEMPORARY_NETWORK_PATTERNS):
            return f"Temporary network error: {error_text}"

        return f"Download failed: {error_text}"

    def _resolve_downloaded_file(self, stdout: str) -> Optional[Path]:
        """Resolve the resulting MP3 path from yt-dlp output with a fallback scan."""
        output_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        for line in reversed(output_lines):
            candidate = Path(line)
            if candidate.suffix.lower() == '.mp3' and candidate.exists():
                return candidate

        mp3_files = list(self.download_dir.glob("*.mp3"))
        if not mp3_files:
            return None
        return max(mp3_files, key=lambda p: p.stat().st_mtime)
    
    @staticmethod
    def get_track_info(url: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Get track information without downloading.
        
        Args:
            url: URL to get info from
            
        Returns:
            Tuple of (success, info_dict, message)
        """
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-warnings',
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = Downloader._classify_download_error(result.stderr)
                return False, None, f"Could not fetch track info: {error_msg}"

            info = json.loads(result.stdout)
            return True, info, "Info fetched successfully"
        
        except json.JSONDecodeError:
            return False, None, "Invalid response from yt-dlp"
        except Exception as e:
            return False, None, f"Error fetching info: {str(e)}"

