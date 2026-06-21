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

## Important Design Rules
- Metadata should be normalized before tagging so downstream code receives predictable values.
- Artwork handling should always prefer a valid embedded image and fall back safely when no usable artwork exists.
- CLI errors should be clear enough for users to act on without reading stack traces.
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

