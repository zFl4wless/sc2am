"""
Core downloader module for sc2am.
Handles downloading audio from various platforms using yt-dlp.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import shutil

logger = logging.getLogger(__name__)


class Downloader:
    """Downloads audio tracks from supported platforms."""
    
    def __init__(self, download_dir: Path):
        """
        Initialize downloader.
        
        Args:
            download_dir: Directory where files will be downloaded
        """
        self.download_dir = Path(download_dir)
        self._check_dependencies()

    @staticmethod
    def _check_dependencies() -> None:
        """Check if yt-dlp is installed."""
        result = shutil.which('yt-dlp')
        if not result:
            raise RuntimeError(
                "yt-dlp is not installed. Install it with: pip install yt-dlp"
            )
        logger.debug("yt-dlp found at: " + result)

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
        
        # yt-dlp command
        output_template = str(self.download_dir / "%(title)s.%(ext)s")
        
        cmd = [
            'yt-dlp',
            '--format', 'bestaudio/best',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '192',
            '--output', output_template,
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
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Download failed: {error_msg}")
                return False, None, f"Download failed: {error_msg}"
            
            # Find the downloaded file
            mp3_files = list(self.download_dir.glob("*.mp3"))
            if not mp3_files:
                return False, None, "No MP3 file found after download"
            
            # Return the most recently modified file
            downloaded_file = max(mp3_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Successfully downloaded: {downloaded_file.name}")
            return True, downloaded_file, f"Downloaded: {downloaded_file.name}"
        
        except subprocess.TimeoutExpired:
            logger.error("Download timeout")
            return False, None, "Download timeout (exceeded 5 minutes)"
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return False, None, f"Unexpected error: {str(e)}"
    
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
                error_msg = result.stderr or "Could not fetch track info"
                return False, None, error_msg
            
            info = json.loads(result.stdout)
            return True, info, "Info fetched successfully"
        
        except json.JSONDecodeError:
            return False, None, "Invalid response from yt-dlp"
        except Exception as e:
            return False, None, f"Error fetching info: {str(e)}"

