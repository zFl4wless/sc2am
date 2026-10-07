"""
Apple Music integration for sc2am.
Handles opening MP3s with Apple Music and playlist management.
"""

import json
import hashlib
import re
import logging
import subprocess
import platform
import time
from pathlib import Path
from typing import List, Optional, Tuple

from mutagen.id3 import ID3, ID3NoHeaderError, COMM

from .history import History
from .music_script import MUSIC_SCRIPT
from .logger import DIAGNOSTIC_HINT

logger = logging.getLogger(__name__)


class AppleMusicManager:
    """Manages interaction with Apple Music on macOS."""

    _MAX_RETRIES = 3
    _RETRY_DELAY_SECONDS = 1.0
    _COMMAND_TIMEOUT_SECONDS = 30
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
            logger.warning(
                "Apple Music manager requires macOS. Current system: " + platform.system()
            )

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
        *,
        read_only: bool = False,
    ) -> Tuple[bool, Optional[subprocess.CompletedProcess], str]:
        """Bound each attempt; retry only operations that cannot import tracks."""
        for attempt in range(1, cls._MAX_RETRIES + 1):
            try:
                completed = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=cls._COMMAND_TIMEOUT_SECONDS
                )
            except subprocess.TimeoutExpired:
                result = None
                error = (
                    f"{operation} timed out after {cls._COMMAND_TIMEOUT_SECONDS} seconds. "
                    "Open Music.app and check for permission prompts or an unresponsive app"
                )
            else:
                if completed.returncode == 0:
                    return True, completed, ""

                result = completed
                error = (completed.stderr or completed.stdout or "Unknown error").strip()

            # Killing open/osascript cannot undo an event already delivered to Music.
            # Even a nonzero exit can follow a partial import, so do not replay it.
            if not read_only:
                return (
                    False,
                    result,
                    f"{error}. This command was not retried because Music may already have "
                    "imported the track. Check the Music library and target playlist before "
                    "repeating the import to avoid duplicates",
                )

            if attempt < cls._MAX_RETRIES and (result is None or cls._is_retryable_error(error)):
                logger.warning(
                    f"{operation} failed temporarily on attempt {attempt}/{cls._MAX_RETRIES}: {error}"
                )
                cls._sleep_before_retry(attempt)
                continue

            return False, result, error

        return False, None, "Unknown error"

    @classmethod
    def _run_osascript(
        cls,
        applescript: str,
        operation: str,
        arguments: Optional[List[str]] = None,
        *,
        read_only: bool = False,
    ) -> Tuple[bool, Optional[subprocess.CompletedProcess], str]:
        command = ["osascript", "-e", applescript, *(arguments or [])]
        return cls._run_command_with_retry(command, operation, read_only=read_only)

    @classmethod
    def open_file_with_music(cls, file_path: Path) -> Tuple[bool, str]:
        """Import and confirm a library track (a successful dispatch is insufficient)."""
        return cls._import(file_path)

    @classmethod
    def add_to_playlist(cls, file_path: Path, playlist_name: str) -> Tuple[bool, str]:
        """Reuse a confirmed library track and verify playlist membership."""
        if not file_path.is_file():
            return False, "The downloaded file was not found."
        resolved, error = cls._resolve_playlist_name(playlist_name)
        if resolved is None:
            return False, error
        return cls._import(file_path, resolved)

    @staticmethod
    def _mark_file(file_path: Path, marker: str) -> None:
        """Put the source marker in the default comment Music reads on import."""
        try:
            tags = ID3(str(file_path))
        except ID3NoHeaderError:
            tags = ID3()
        comments = tags.getall("COMM")
        existing = next(
            (frame for frame in comments if frame.desc == "" and frame.lang == "eng"), None
        )
        text = "\n".join(existing.text) if existing else ""
        if marker not in text:
            tags.add(COMM(encoding=3, lang="eng", desc="", text=[(text + "\n" + marker).strip()]))
            tags.save(str(file_path), v2_version=3)

    @classmethod
    def _music_state(
        cls,
        path: Path,
        playlist: str,
        marker: str,
        track_id: str = "",
        library_id: str = "",
        action: str = "lookup",
        playlist_id: str = "",
    ) -> dict:
        success, result, error = cls._run_osascript(
            MUSIC_SCRIPT,
            "Checking Music import" if action == "lookup" else "Importing into Music",
            [str(path), playlist, marker, track_id, library_id, action, playlist_id],
            read_only=action == "lookup",
        )
        if not success or result is None:
            raise RuntimeError(error or "Music did not return a confirmed track reference.")
        fields = result.stdout.strip().split("|")
        if (
            len(fields) != 4
            or not re.fullmatch(r"[0-9A-Fa-f]{16}", fields[0])
            or any(value and not re.fullmatch(r"[0-9A-Fa-f]{16}", value) for value in fields[1:3])
            or fields[3] not in ("0", "1")
            or (bool(playlist) != bool(fields[2]))
            or (fields[3] == "1" and (not fields[1] or not fields[2]))
            or (library_id and library_id != fields[0])
            or (playlist_id and playlist_id != fields[2])
        ):
            raise RuntimeError("Music did not return a valid library/track confirmation.")
        return dict(library=fields[0], track=fields[1], playlist=fields[2], member=fields[3] == "1")

    @classmethod
    def _import(cls, file_path: Path, playlist: str = "") -> Tuple[bool, str]:
        if not file_path.is_file():
            return False, "The downloaded file was not found."
        if file_path.suffix.lower() != ".mp3":
            return False, "The selected file is not an MP3."
        if file_path.is_symlink():
            return False, "Use the verified MP3 file, not a symbolic link."
        path = file_path.resolve()
        try:
            with History(path.parent) as history, history.music_lock():
                source = history.file_source(path)
                marker = "sc2am:" + hashlib.sha256(source.encode()).hexdigest()
                # Discover the active library before using a stored persistent ID.
                state = cls._music_state(path, playlist, marker)
                key = "music:" + state["library"] + ":" + source
                known = history.get(key) or ""
                if known:
                    state = cls._music_state(path, playlist, marker, known, state["library"])
                for stage in (["import", "playlist"] if playlist else ["import"]):
                    pending = (
                        key
                        + ":pending:"
                        + (state["playlist"] if stage == "playlist" else "library")
                    )
                    confirmed = bool(state["track"]) if stage == "import" else state["member"]
                    if confirmed:
                        history.put(key, state["track"])
                        history.delete(pending)
                        continue
                    if history.get(pending):
                        raise RuntimeError(
                            "A previous Music mutation is still unconfirmed and was not repeated. "
                            "Check the Music library and target playlist, then rerun to reconcile. "
                            "If still unresolved, follow docs/music-import-validation.md before clearing the pending record."
                        )
                    if stage == "import":
                        cls._mark_file(path, marker)
                        history.refresh_file(path, source)
                    # Commit intent BEFORE sending the event. A crash, timeout or
                    # lost response must leave a durable barrier against replay.
                    history.put(pending, {"path": str(path), "stage": stage, "playlist": playlist})
                    mutation_error = ""
                    try:
                        changed = cls._music_state(
                            path,
                            playlist,
                            marker,
                            state["track"],
                            state["library"],
                            stage,
                            state["playlist"],
                        )
                        if changed["track"]:
                            history.put(key, changed["track"])
                    except RuntimeError as exc:
                        mutation_error = str(exc)
                        if "SC2AM_NOT_STARTED:" in mutation_error:
                            history.delete(pending)
                            raise
                    # Read-only reconciliation also handles a timed-out event that
                    # Music completed. No mutating subprocess is blindly retried.
                    state = cls._music_state(
                        path,
                        playlist,
                        marker,
                        history.get(key) or state["track"],
                        state["library"],
                        playlist_id=state["playlist"],
                    )
                    confirmed = bool(state["track"]) if stage == "import" else state["member"]
                    if not confirmed:
                        raise RuntimeError(
                            (mutation_error + " " if mutation_error else "")
                            + "Music has not confirmed the requested change. The MP3 is retained; "
                            "rerun to reconcile without redownloading. Check the Music library and target playlist."
                        )
                    history.put(key, state["track"])
                    history.delete(pending)
                return True, (
                    f"Added to playlist '{playlist}'"
                    if playlist
                    else "Import confirmed in Apple Music"
                )
        except Exception as exc:
            logger.exception("Could not confirm Music import")
            return False, (
                f"Could not confirm the Music import: {exc}. "
                "Open Music.app and check Automation permissions in System Settings > Privacy & Security. "
                f"{DIAGNOSTIC_HINT}"
            )

    @staticmethod
    def get_playlists() -> Tuple[bool, List[str], str]:
        """
        Get list of available playlists in Apple Music.

        Returns:
            Tuple of (success, playlist_names, message)
        """
        applescript = """
        use framework "Foundation"
        use scripting additions
        tell application "Music"
            set playlistNames to name of playlists
        end tell
        set namesArray to current application's NSArray's arrayWithArray:playlistNames
        set jsonData to current application's NSJSONSerialization's dataWithJSONObject:namesArray options:0 |error|:(missing value)
        return (current application's NSString's alloc()'s initWithData:jsonData encoding:(current application's NSUTF8StringEncoding)) as text
        """

        try:
            success, result, error = AppleMusicManager._run_osascript(
                applescript,
                "Fetching playlists",
                read_only=True,
            )

            if not success or result is None:
                logger.error(f"Failed to get playlists: {error}")
                return (
                    False,
                    [],
                    f"Could not retrieve playlists from Apple Music: {error}. Ensure Music.app is installed and that Automation permissions are granted.",
                )

            # JSON preserves punctuation, Unicode, whitespace and duplicate names.
            playlists = json.loads(result.stdout)
            if not isinstance(playlists, list) or not all(
                isinstance(name, str) for name in playlists
            ):
                raise ValueError("Expected a JSON array of playlist names")
            if not playlists:
                return True, [], "No playlists found"

            logger.debug(f"Found {len(playlists)} playlists")
            return True, playlists, "Playlists retrieved"

        except Exception:
            logger.exception("Error fetching playlists")
            return (
                False,
                [],
                "Could not retrieve playlists from Apple Music due to an unexpected error. "
                f"Confirm Music.app is installed and accessible. {DIAGNOSTIC_HINT}",
            )

    @staticmethod
    def _resolve_playlist_name(playlist_name: str) -> Tuple[Optional[str], str]:
        normalized_name = playlist_name.strip()
        if not normalized_name:
            return None, "Please provide a playlist name."

        success, playlists, message = AppleMusicManager.get_playlists()
        if not success:
            return None, message

        matches = [
            playlist
            for playlist in playlists
            if playlist.strip().lower() == normalized_name.lower()
        ]
        if not matches:
            return (
                None,
                f'Playlist "{normalized_name}" was not found in Apple Music. Please check the name and try again.',
            )

        if len(matches) > 1:
            return (
                None,
                f'Multiple playlists named "{normalized_name}" were found in Apple Music. Please rename one of them or choose a unique playlist name.',
            )

        return matches[0], f'Playlist "{matches[0]}" selected.'
