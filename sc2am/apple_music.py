"""
Apple Music integration for sc2am.
Handles opening MP3s with Apple Music and playlist management.
"""

import logging
import subprocess
import platform
from pathlib import Path
from typing import Tuple

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
                error = result.stderr or "Unknown error"
                logger.error(f"Failed to open file with Music app: {error}")
                return False, "Could not open the file in Apple Music. Make sure Apple Music is installed and allowed to automate."

            logger.info(f"Opened {file_path.name} with Apple Music")
            return True, f"Opened with Apple Music"
        
        except Exception as e:
            logger.exception("Error opening file in Apple Music")
            return False, "Could not open the file in Apple Music. Please check the log file for details."

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

        # AppleScript to add track to playlist
        applescript = f'''
        tell application "Music"
            activate
            set sourcePath to POSIX file "{str(file_path)}"
            add sourcePath to playlist "{playlist_name}"
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error = result.stderr or "Unknown error"
                logger.warning(f"Failed to add to playlist: {error}")
                return False, "Could not add the track to the playlist. Check that the playlist exists and Apple Music automation is allowed."

            logger.info(f"Added {file_path.name} to playlist '{playlist_name}'")
            return True, f"Added to playlist '{playlist_name}'"
        
        except Exception as e:
            logger.exception("Error running AppleScript")
            return False, "Could not add the track to the playlist. Please check the log file for details."

    @staticmethod
    def get_playlists() -> Tuple[bool, list, str]:
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
                error = result.stderr or "Unknown error"
                logger.error(f"Failed to get playlists: {error}")
                return False, [], "Could not retrieve playlists from Apple Music."

            # Parse output - AppleScript returns comma-separated names
            output = result.stdout.strip()
            if not output:
                return True, [], "No playlists found"
            
            playlists = [p.strip() for p in output.split(',')]
            logger.debug(f"Found {len(playlists)} playlists")
            return True, playlists, "Playlists retrieved"
        
        except Exception as e:
            logger.exception("Error fetching playlists")
            return False, [], "Could not retrieve playlists from Apple Music."

