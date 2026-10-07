# Architecture Overview

SC2AM is a small command-line application that downloads a SoundCloud track, enriches the resulting MP3 with metadata, and opens the file in Apple Music on macOS.

## High-Level Flow
1. The CLI in `main.py` validates the user input.
2. `sc2am/validator.py` checks whether a URL or batch file entry is supported.
3. `sc2am/downloader.py` uses `yt-dlp` to fetch track information and download audio.
4. `sc2am/metadata.py` normalizes metadata, writes ID3 tags, and embeds cover art.
5. `sc2am/apple_music.py` opens the final MP3 in Music.app and optionally adds it to a playlist.
6. `sc2am/config_manager.py` provides defaults, configuration files, and environment-variable overrides.
7. `sc2am/logger.py` sets up application logging.

## Module Responsibilities

| Module                    | Responsibility                                                                 |
|---------------------------|--------------------------------------------------------------------------------|
| `main.py`                 | CLI commands, argument handling, and user-facing status output                 |
| `sc2am/validator.py`      | Strict URL validation and batch-file validation                                |
| `sc2am/downloader.py`     | Download orchestration, error classification, and metadata hand-off            |
| `sc2am/metadata.py`       | Metadata normalization, tag writing, artwork extraction, and fallback handling |
| `sc2am/apple_music.py`    | macOS Music.app automation and playlist operations                             |
| `sc2am/config_manager.py` | Configuration defaults, loading, and persistence                               |
| `sc2am/logger.py`         | Logging setup                                                                  |

The [CLI and configuration contract](cli-and-config-contract.md) defines source
precedence, supported settings, and command behavior. Single-URL, multi-URL, and
batch commands share one processing loop; configuration loads only when needed so
help and initialization remain available even with broken configuration.

Playlist imports use fixed AppleScript logic and pass the resolved absolute
track path and playlist name as separate `osascript` arguments. User-provided
names and paths are not interpolated into script source.
Playlist names are serialized as a JSON array using macOS Foundation so commas,
Unicode, quotes and embedded whitespace survive listing and resolution. The import
script rechecks that exactly one playlist matches and that it is a regular user
playlist, then adds the file to that object. Smart, Genius, folder and system
playlists are rejected with an actionable error.

All Music subprocess attempts (`open` and `osascript`) use a 30-second timeout.
Only read-only playlist lookups opt into retries: at most three attempts with
1- and 2-second backoff delays. Importing commands are never automatically
replayed after a failure, including AppleEvent timeout errors and subprocess
timeouts, because Music may already have applied the mutation. Their warning
asks users to inspect the library and playlist before repeating the import.
Subprocess termination does not undo a delivered Music event. Confirmed library
references, import reconciliation and safe repeat/resume across runs remain
separate work in #80; the existing success and CLI warning contracts are preserved.

Before downloading, the downloader validates the URL and requires a successful
single-track extraction. Metadata uses `--dump-single-json --flat-playlist
--playlist-end 1` to preserve the collection envelope without extracting every
entry or downloading audio. Results containing `entries` or a non-track `_type`
are rejected, including empty and single-entry collections. Failed extraction
also stops the workflow. `--no-playlist` is an additional download precaution.

Both yt-dlp commands include `--ignore-config`, so external yt-dlp configuration
files cannot add archives, filters, or skip-download settings. SC2AM's CLI,
environment, YAML, and default precedence remains unchanged.

The downloader accepts only the single final path reported by its own yt-dlp
process after post-processing. The path must identify a regular MP3 file directly
inside the configured download directory; symlinks and ambiguous output are
rejected. Paths are JSON-encoded to preserve special characters. If verification
fails after retries, the command reports a download failure without tagging or
importing any file. It never selects another MP3 by scanning the directory.

The output template is `%(title)s [%(id)s].%(ext)s`, so different SoundCloud
track IDs cannot collide merely because their titles match. yt-dlp is called with
`--no-overwrites`: repeats with the same ID and title reuse existing audio, then
SC2AM refreshes tags and applies the configured Music actions. A changed title
creates a new path; legacy title-only files are not migrated or reused.

## Important Design Rules
- Metadata should be normalized before tagging so downstream code receives predictable values.
- Artwork responses are streamed with a 10 MiB cap and a 20-second total-time budget. Image bytes must decode successfully and stay under the pixel limit before SC2AM resizes and embeds them as JPEG; a fallback is reported separately from verified downloaded artwork.
- CLI errors should be clear enough for users to act on without reading stack traces.
- CLI exit codes should stay stable (`0` success, `1` processing failure, `2` usage/config input error) so automation can rely on them.
- The project should remain macOS-friendly but avoid hard-coding local paths or machine-specific assumptions.

## macOS Setup Notes

Apple Music automation depends on local macOS permissions and a working Music.app installation. The user-facing setup checklist lives in [`docs/macos-setup.md`](macos-setup.md), and the README links there as well.

## Testing Focus
The most important tests cover:
- URL validation
- configuration loading and defaults
- download error classification
- metadata normalization and tag writing
- cover art fallback behavior
- Apple Music open/add behavior on macOS-specific paths

## Release Notes
When preparing a release, verify that the code version and package version match, then summarize user-visible improvements in release notes.
