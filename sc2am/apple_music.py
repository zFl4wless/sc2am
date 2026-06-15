"""
Apple Music integration for sc2am.
Handles opening MP3s with Apple Music and playlist management.
"""

import logging
import subprocess
import platform
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class AppleMusicManager:
    """Manages interaction with Apple Music on macOS."""
    
    def __init__(self):
        """Initialize Apple Music manager."""
        self._check_platform()
    
    @staticmethod
    def _check_platform() -> None:
        """Verify running on macOS."""
        if platform.system() != "Darwin":
            logger.warning("Apple Music manager requires macOS. Current system: " + platform.system())
    
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
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error = (result.stderr or result.stdout or "Unknown error").strip()
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
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error = (result.stderr or result.stdout or "Unknown error").strip()
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
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error = (result.stderr or result.stdout or "Unknown error").strip()
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

