# Architecture Overview

SC2AM is a small command-line application that downloads a SoundCloud track, enriches the resulting MP3 with metadata, and confirms an import into Apple Music on macOS.

## High-Level Flow
1. The CLI in `main.py` validates the user input.
2. `sc2am/validator.py` checks whether a URL or batch file entry is supported.
3. `sc2am/downloader.py` uses `yt-dlp` to fetch track information and download audio.
4. `sc2am/metadata.py` normalizes metadata, writes ID3 tags, and embeds cover art.
5. `sc2am/apple_music.py` confirms the final MP3 in Music.app and optionally verifies playlist membership.
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
| `sc2am/history.py`       | Durable download evidence, library references and pending mutations           |
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
workflow lists playlist names and resolves a writable target once per run, lazily
after the first successful download. Both the selected library and playlist
persistent IDs are pinned for subsequent playlist imports. Each track still
checks those IDs and the destination type before mutations; a deleted/replaced
playlist or a changed library fails explicitly instead of selecting another
playlist with the same name. A renamed playlist with the same ID remains the
selected object. Smart, Genius, folder and system playlists are rejected with an
actionable error. Unavailable/ambiguous targets are reported for affected tracks
without repeating name resolution during that run. A new invocation resolves
again; `--dry-run` and disabled playlist actions never resolve Music targets.

All Music subprocess attempts use a 30-second timeout. Read-only queries retry
at most three times, with 1- and 2-second backoff. Fixed AppleScript returns
validated library/track/playlist persistent IDs and membership, not a dispatch
acknowledgement. The active library (and optional destination) is first resolved
without searching for tracks. The library ID scopes recorded references; the
subsequent lookup prefers the saved track ID for that library, even if comments
were edited or marker matches are ambiguous. A library track is
found by a confirmed persistent ID, a stable source marker in its comment, or
its original file location. Playlist additions duplicate the existing library
reference only if membership is absent; they do not re-add the MP3.

`History` stores evidence in a SQLite journal inside `<download_dir>/.sc2am`.
Downloaded files are indexed by the validated URL and SoundCloud ID; reuse
requires a regular file in the same directory with the recorded SHA-256 hash.
An exact known URL can resume offline. Metadata is not refreshed on reuse.
Before a new import, canonical source markers (`sc2am:` followed by 64 lowercase
hexadecimal characters) are removed from all ID3 COMM comment texts, including
markers embedded in ordinary text. Ordinary comment text, languages and
descriptions are retained. Exactly one marker for the current source is then
written to the English default comment; repeating this produces the same result.
The journal records the resulting file hash. This allows Music's copied files to
be located even when an import response is lost.

This hardens track association; a reachable remote attack has not been confirmed.
Existing Music entries and their comments are not retroactively cleaned. Marker
and location lookup remain fallbacks when a saved ID is absent or no longer
resolves; ambiguous matches stop before mutation. Synthetic ID3 files and process
doubles verify the application workflow. Native Music comment selection across
COMM frames and provider metadata behavior remain open questions that require
separate isolated acceptance testing; these tests do not establish remote
exploitability or cloud behavior.

A nonblocking file lock serializes Music operations using the same download
folder. Each mutation commits a pending intent before dispatch and performs an
independent read-only confirmation afterward. An uncertain result remains pending
across process restarts and is never blindly replayed. A later read can reconcile
it. Explicit script errors before the mutation clear intent so corrected targets
can be retried; generic errors/timeouts do not. Confirmed references are checked
live, including playlist membership removed since the previous run. Missing
confirmed tracks can be reimported. Failed writes/corrupt journals stop the Music
stage instead of silently resetting history. Cross-directory concurrent imports,
legacy copied imports without markers, and manual edits to cached audio require
manual care; there is no cross-machine or cloud idempotency guarantee.

See [Music validation and recovery](music-import-validation.md) for the isolated
macOS acceptance procedure and the distinction between automated and live evidence.

Before downloading, the downloader validates the URL and requires a successful
single-track extraction. Metadata uses `--dump-single-json --flat-playlist
--playlist-end 1` to preserve the collection envelope without extracting every
entry or downloading audio. Results containing `entries` or a non-track `_type`
are rejected, including empty and single-entry collections. Failed extraction
also stops the workflow. The complete single-track JSON (including formats) is
passed to the download command using `--load-info-json` in a private temporary
file, then removed on success or failure. The same extraction supplies ID3
metadata and history identity. This avoids a second URL extraction while
retaining two bounded yt-dlp subprocesses per fresh track. `--no-playlist` is an
additional download precaution. See the [yt-dlp filesystem options](https://github.com/yt-dlp/yt-dlp#filesystem-options).

The download-only copy omits `webpage_url` to disable yt-dlp's automatic URL
re-extraction on media failure, which could bypass the collection preflight or
change the track identity/metadata. Original metadata is retained for tagging.
Temporary failures retry the checked extraction; an expired media URL fails
without recording a successful download. Rerunning performs a fresh preflight
when there is no verified cached file. Exact-URL and source-ID download reuse,
file verification and durable Music mutation barriers remain unchanged.
See [isolated workflow measurements](workflow-performance.md) for call counts,
reproduction commands and the limits of simulated timings.

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
`--no-overwrites` for downloads without reusable journal evidence. Once recorded,
the source ID determines reuse even after title changes; legacy title-only files
are not migrated or reused.

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
