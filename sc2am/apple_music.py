"""
Apple Music integration for sc2am.
Handles opening MP3s with Apple Music and playlist management.
"""

import logging
import subprocess
import platform
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class AppleMusicManager:
    """Manages interaction with Apple Music on macOS."""

    _MAX_RETRIES = 3
    _RETRY_DELAY_SECONDS = 1.0
    _RETRYABLE_PATTERNS = (
        "appleevent timed out",
        "application isn't responding",
        "application is not responding",
        "busy",
        "connection refused",
        "connection reset",
        "gateway timeout",
        "service unavailable",
        "temporarily unavailable",
        "temporary failure",
        "timed out",
        "timeout",
        "try again",
    )

    def __init__(self):
        """Initialize Apple Music manager."""
        self._check_platform()
    
    @staticmethod
    def _check_platform() -> None:
        """Verify running on macOS."""
        if platform.system() != "Darwin":
            logger.warning("Apple Music manager requires macOS. Current system: " + platform.system())

    @classmethod
    def _is_retryable_error(cls, stderr: str) -> bool:
        lowered = (stderr or "").lower()
        return any(pattern in lowered for pattern in cls._RETRYABLE_PATTERNS)

    @classmethod
    def _sleep_before_retry(cls, attempt: int) -> None:
        time.sleep(cls._RETRY_DELAY_SECONDS * attempt)

    @classmethod
    def _run_command_with_retry(
        cls,
        cmd: list[str],
        operation: str,
    ) -> Tuple[bool, Optional[subprocess.CompletedProcess], str]:
        for attempt in range(1, cls._MAX_RETRIES + 1):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return True, result, ""

            error = (result.stderr or result.stdout or "Unknown error").strip()
            if attempt < cls._MAX_RETRIES and cls._is_retryable_error(error):
                logger.warning(
                    f"{operation} failed temporarily on attempt {attempt}/{cls._MAX_RETRIES}: {error}"
                )
                cls._sleep_before_retry(attempt)
                continue

            return False, result, error

        return False, None, "Unknown error"

    @classmethod
    def _run_osascript(cls, applescript: str, operation: str) -> Tuple[bool, Optional[subprocess.CompletedProcess], str]:
        return cls._run_command_with_retry(['osascript', '-e', applescript], operation)

    @staticmethod
    def open_file_with_music(file_path: Path) -> Tuple[bool, str]:
        """
        Open MP3 file with Apple Music.
        
        Args:
            file_path: Path to MP3 file
            
        Returns:
            Tuple of (success, message)
        """
        if not file_path.exists():
            return False, "The downloaded file was not found."

        if not file_path.suffix.lower() == '.mp3':
            return False, "The selected file is not an MP3."

        try:
            # Use 'open' command with -a flag to open with specific app
            cmd = ['open', '-a', 'Music', str(file_path)]
            success, result, error = AppleMusicManager._run_command_with_retry(
                cmd,
                "Opening file with Music",
            )

            if not success:
                logger.error(f"Failed to open file with Music app: {error}")
                # Provide an actionable message that surfaces the underlying error
                return (
                    False,
                    f"Apple Music could not be opened: {error}.\n"
                    "Ensure Apple Music is installed and that this application is allowed to open/automate it. "
                    "If a permissions prompt appeared, grant access in System Settings -> Privacy & Security.",
                )

            logger.info(f"Opened {file_path.name} with Apple Music")
            return True, f"Opened with Apple Music"
        
        except Exception:
            logger.exception("Error opening file in Apple Music")
            return (
                False,
                "Could not open the file in Apple Music due to an unexpected error. "
                "Please check the log file for details and ensure Music.app is installed and accessible.",
            )

    @staticmethod
    def add_to_playlist(file_path: Path, playlist_name: str) -> Tuple[bool, str]:
        """
        Add track to Apple Music playlist via AppleScript.
        
        Args:
            file_path: Path to MP3 file
            playlist_name: Name of target playlist
            
        Returns:
            Tuple of (success, message)
        """
        if not file_path.exists():
            return False, "The downloaded file was not found."

        resolved_playlist, error_message = AppleMusicManager._resolve_playlist_name(playlist_name)
        if resolved_playlist is None:
            return False, error_message

        # AppleScript to add track to playlist
        applescript = f'''
        tell application "Music"
            activate
            set sourcePath to POSIX file "{str(file_path)}"
            add sourcePath to playlist "{resolved_playlist}"
        end tell
        '''
        
        try:
            success, result, error = AppleMusicManager._run_osascript(
                applescript,
                "Adding track to playlist",
            )

            if not success:
                logger.warning(f"Failed to add to playlist: {error}")
                return (
                    False,
                    f"Failed to add the track to playlist '{resolved_playlist}': {error}.\n"
                    "Verify the playlist exists, Music.app is running, and that this application is allowed to control Music (System Settings -> Privacy & Security -> Automation).",
                )

            logger.info(f"Added {file_path.name} to playlist '{resolved_playlist}'")
            return True, f"Added to playlist '{resolved_playlist}'"

        except Exception:
            logger.exception("Error running AppleScript")
            return (
                False,
                "Could not add the track to the playlist due to an unexpected error. "
                "Please check the log file for details and confirm Music.app can be automated by this process.",
            )

    @staticmethod
    def get_playlists() -> Tuple[bool, List[str], str]:
        """
        Get list of available playlists in Apple Music.
        
        Returns:
            Tuple of (success, playlist_names, message)
        """
        applescript = '''
        tell application "Music"
            return name of playlists
        end tell
        '''
        
        try:
            success, result, error = AppleMusicManager._run_osascript(
                applescript,
                "Fetching playlists",
            )

            if not success:
                logger.error(f"Failed to get playlists: {error}")
                return (
                    False,
                    [],
                    f"Could not retrieve playlists from Apple Music: {error}. Ensure Music.app is installed and that Automation permissions are granted.",
                )

            # Parse output - AppleScript returns comma-separated names
            output = result.stdout.strip()
            if not output:
                return True, [], "No playlists found"
            
            playlists = [p.strip() for p in output.split(',') if p.strip()]
            logger.debug(f"Found {len(playlists)} playlists")
            return True, playlists, "Playlists retrieved"
        
        except Exception:
            logger.exception("Error fetching playlists")
            return (
                False,
                [],
                "Could not retrieve playlists from Apple Music due to an unexpected error. "
                "Please check the log file and confirm Music.app is installed and accessible.",
            )

    @staticmethod
    def _resolve_playlist_name(playlist_name: str) -> Tuple[Optional[str], str]:
        normalized_name = playlist_name.strip()
        if not normalized_name:
            return None, "Please provide a playlist name."

        success, playlists, message = AppleMusicManager.get_playlists()
        if not success:
            return None, message

        matches = [playlist for playlist in playlists if playlist.lower() == normalized_name.lower()]
        if not matches:
            return None, f'Playlist "{normalized_name}" was not found in Apple Music. Please check the name and try again.'

        if len(matches) > 1:
            return (
                None,
                f'Multiple playlists named "{normalized_name}" were found in Apple Music. Please rename one of them or choose a unique playlist name.',
            )

        return matches[0], f'Playlist "{matches[0]}" selected.'

