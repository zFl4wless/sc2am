"""Opt-in live acceptance test. Run ONLY against an isolated Music test library.

See docs/music-import-validation.md. This script adds three generated MP3s and
playlist entries; it never cleans up or changes library selection automatically.
"""

import argparse
import json
import platform
from pathlib import Path
import subprocess
import uuid

from mutagen.id3 import ID3

from sc2am.apple_music import AppleMusicManager as Manager
from sc2am.music_script import MUSIC_SCRIPT

CHECK_SCRIPT = """
on run argv
    set expectedLibrary to item 1 of argv
    tell application "Music"
        set actualLibrary to persistent ID of container of library playlist 1
        if actualLibrary is not expectedLibrary then error "Wrong active Music library; stopped."
        return actualLibrary
    end tell
end run
"""

EVIDENCE_SCRIPT = """
use framework "Foundation"
use scripting additions
on run argv
    set expectedLibrary to item 1 of argv
    set sourceMarker to item 2 of argv
    set targetName to item 3 of argv
    tell application "Music"
        set libraryPlaylist to library playlist 1
        if persistent ID of container of libraryPlaylist is not expectedLibrary then error "Wrong active library."
        set matchingTracks to every file track of libraryPlaylist whose comment contains sourceMarker
        if (count of matchingTracks) is not 1 then error "Expected exactly one source marker in the library."
        set libraryTrack to item 1 of matchingTracks
        set trackID to persistent ID of libraryTrack
        set trackLocation to get location of libraryTrack
        set libraryLocation to POSIX path of trackLocation
        set matchingPlaylists to every user playlist whose name is targetName
        if (count of matchingPlaylists) is not 1 then error "Expected one target playlist."
        set destinationPlaylist to item 1 of matchingPlaylists
        set memberCount to count of (every track of destinationPlaylist whose persistent ID is trackID)
        if memberCount is not 1 then error "Expected exactly one playlist membership."
    end tell
    set valuesArray to current application's NSArray's arrayWithArray:{trackID, libraryLocation}
    set jsonData to current application's NSJSONSerialization's dataWithJSONObject:valuesArray options:0 |error|:(missing value)
    return (current application's NSString's alloc()'s initWithData:jsonData encoding:(current application's NSUTF8StringEncoding)) as text
end run
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-id", required=True, help="Persistent ID of the isolated library")
    parser.add_argument("--playlist", required=True, help="Existing regular test playlist")
    parser.add_argument(
        "--directory", type=Path, required=True, help="New directory for fixtures/evidence"
    )
    parser.add_argument("--confirm-isolated-library", action="store_true", required=True)
    parser.add_argument(
        "--expect-copied", action="store_true", help="Require Music to copy imported files"
    )
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("This live acceptance test requires macOS.")
    original_descriptor = Manager.__dict__["_run_osascript"]
    original = Manager._run_osascript
    success, result, error = original(
        CHECK_SCRIPT, "Checking isolated library", [args.library_id], read_only=True
    )
    if not success or result is None or result.stdout.strip() != args.library_id:
        raise RuntimeError(error or "Active library ID was not confirmed.")
    args.directory.mkdir(parents=True, exist_ok=False)
    evidence = {
        "macos": platform.mac_ver()[0],
        "library": args.library_id,
        "playlist": args.playlist,
        "cases": [],
    }
    fault = {"mode": "", "injected": []}
    mutations = []

    def guarded(cls, script, operation, arguments=None, *, read_only=False):
        arguments = list(arguments or [])
        if script == MUSIC_SCRIPT:
            # Pin every read AND mutation, even initial discovery, to this library.
            arguments[4] = args.library_id
            stage = arguments[5]
            if stage != "lookup":
                mutations.append(stage)
                if (
                    fault["mode"] == "partial"
                    and stage == "playlist"
                    and stage not in fault["injected"]
                ):
                    fault["injected"].append(stage)
                    return False, None, "SC2AM_NOT_STARTED: Simulated pre-mutation playlist failure"
                response = original(script, operation, arguments, read_only=read_only)
                if fault["mode"] == "lost_reply" and stage not in fault["injected"]:
                    if not response[0]:
                        raise RuntimeError(
                            "Real mutation failed before lost-reply simulation: " + response[2]
                        )
                    fault["injected"].append(stage)
                    return False, None, "Simulated lost mutation reply (event already delivered)"
                return response
        return original(script, operation, arguments, read_only=read_only)

    Manager._run_osascript = classmethod(guarded)
    try:
        for index, case in enumerate(("repeat", "lost_reply", "partial")):
            fault.update(mode=case, injected=[])
            mutations.clear()
            path = args.directory.resolve() / f'{case} "été".mp3'
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    f"sine=frequency={440 + index * 110}:duration=1",
                    "-metadata",
                    f"title=SC2AM {case} {uuid.uuid4()}",
                    str(path),
                ],
                check=True,
                timeout=30,
            )
            first, message = Manager.add_to_playlist(path, args.playlist)
            if first != (case != "partial"):
                raise RuntimeError(f"{case}: unexpected first result: {message}")
            for _ in range(2):
                success, message = Manager.add_to_playlist(path, args.playlist)
                if not success:
                    raise RuntimeError(f"{case}: repeat failed: {message}")
            expected = (
                ["import", "playlist", "playlist"] if case == "partial" else ["import", "playlist"]
            )
            if mutations != expected:
                raise RuntimeError(f"{case}: unexpected mutation sequence {mutations}")
            marker = ID3(path)["COMM::eng"].text[0]
            success, result, error = original(
                EVIDENCE_SCRIPT,
                "Reading live evidence",
                [args.library_id, marker, args.playlist],
                read_only=True,
            )
            if not success or result is None:
                raise RuntimeError(error or "Missing evidence")
            track_id, location = json.loads(result.stdout)
            copied = Path(location).resolve() != path
            if args.expect_copied and not copied:
                raise RuntimeError(
                    "Music did not copy the imported file; enable copying and repeat in a new directory."
                )
            evidence["cases"].append(
                {
                    "case": case,
                    "track_id": track_id,
                    "library_location": location,
                    "copied": copied,
                    "mutations": list(mutations),
                    "source_matches": 1,
                    "playlist_memberships": 1,
                }
            )
            (args.directory / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(f"PASS: {case}; track {track_id}; one library track, one playlist entry")
    finally:
        Manager._run_osascript = original_descriptor
    print(f"Evidence: {args.directory / 'evidence.json'}")


if __name__ == "__main__":
    main()
