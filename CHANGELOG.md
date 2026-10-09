# Changelog

All notable user-facing changes to SC2AM are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases use [Semantic Versioning](https://semver.org/).

## [Unreleased]

Changes merged after the latest release will be collected here until the next
release is prepared.

## [2.1.1] - 2026-10-09

### Fixed

- Before a new Music import, replaces pre-existing SC2AM source markers in all
  ID3 comments, including embedded markers and ASCII case variants, with one
  marker for the current track. Ordinary comment text is retained.
- Resolves the active Music library before searching for tracks and prefers its
  saved track ID over conflicting comment markers. Repeat/resume and uncertain
  mutation safeguards remain in place.

### Changed

- Clarifies the supported CLI/MP3 workflow and project presentation. The optional
  clipboard entry point and source-preserving output formats remain deferred.

Existing Music entries are not retroactively cleaned. Native Music/provider
behavior was not newly tested; no reachable remote attack has been confirmed.
See the [release notes](docs/releases/v2.1.1.md) for upgrade and validation limits.

## [2.1.0] - 2026-10-08

This compatible minor release combines the completed v2.0.2 and v2.1.0
milestone work. **v2.0.2 is skipped**; it was never tagged or published.
See the [release notes](docs/releases/v2.1.0.md) for upgrade guidance,
acceptance evidence and release verification.

### Added

- Confirmed local Music imports and playlist membership, with a download-folder
  journal that reuses verified MP3s and reconciles interrupted Music operations
  before sending another import. Keep the downloads and `.sc2am` journal together.
- Separate download, import and playlist summaries, including partial success.
  Opt-in `--strict-import` returns exit code 1 for failed or unconfirmed Music
  stages; default Music failures remain warnings.
- Read-only `sc2am doctor` checks for runtime dependencies, download-directory
  accessibility and basic macOS prerequisites without accessing the Music library.
- Bounded resolution of mobile `on.soundcloud.com` share links to single tracks
  in `download` and `batch`; share-link dry runs also require network access.
- A Mac-to-iPhone, offline and CarPlay setup guide, a manual acceptance record,
  and a captioned 36-second animated overview. Device playback is owner-reported;
  the film illustrates the journey and is not a live recording.

### Fixed

- Music paths and playlist names containing commas, quotes or Unicode are passed
  safely; duplicate names and non-writable playlist types produce clear errors.
- Music subprocess timeouts are bounded. Read-only lookups retry transient
  failures; uncertain imports are reconciled rather than blindly repeated.
- Download and Music errors explain how to enable diagnostics when no log file
  is configured; configured logs retain underlying errors and tracebacks.
- Artwork downloads have byte/time limits, validate actual image content and
  normalize supported images to JPEG, with a reported fallback when needed.

### Changed

- Reused the checked track extraction for audio downloads and resolved the target
  playlist once per run, reducing repeated work without claiming faster cloud sync.
- Raised dependency minimums for Click, idna and urllib3, added Pillow for artwork
  validation, and added runtime dependency auditing and application type checks
  to CI. Packages declare the MIT SPDX expression and include the license file.
- Clarified installation, dependency upgrades, safe journal retention and recovery.
  Python 3.10+ remains supported; no configuration keys are removed in this release.

## [2.0.1] - 2026-10-05

### Fixed

- Prevented downloads from tagging or reusing unrelated files and rejected
  SoundCloud collections in the single-track workflow.
- Reported download-directory and missing FFmpeg/ffprobe setup failures with
  actionable guidance.

### Changed

- Isolated SC2AM downloads from personal yt-dlp configuration.
- Added cross-platform build, install, and CLI smoke checks for release artifacts.
- Clarified the supported release line and private vulnerability reporting path.

## [2.0.0] - 2026-10-01

### Added

- Added a repeatable release checklist and changelog workflow.
- Added dry-run, batch-processing, retry, logging, and configuration guidance
  across the CLI documentation.

### Changed

- Improved CLI configuration precedence, validation, error reporting, and
  Apple Music automation guidance.
- Expanded regression coverage for downloader and Apple Music workflows.

### Removed

- Removed the inactive `music_library_path`, `keep_downloads`,
  `normalize_metadata`, and `skip_existing_tracks` configuration settings and
  their environment variables. Existing configuration files using these keys
  must be updated before upgrading.

## [1.4.1] - 2026-08-03

### Changed

- Improved CLI configuration, validation, logging, dry-run, and batch workflows.
- Added clearer Apple Music automation guidance and actionable error messages.
- Hardened metadata handling and retry behavior for transient failures.
- Updated dependencies to address security advisories.

## Release entry format

Use the following headings when adding user-facing changes:

- **Added** for new capabilities.
- **Changed** for changes to existing behavior.
- **Fixed** for bug fixes.
- **Removed** for removed or deprecated behavior.

Keep entries concise and describe the impact for users, not internal
implementation details. Move the relevant entries from `Unreleased` into a
dated version section when releasing.

[Unreleased]: https://github.com/zfl4wless/sc2am/compare/v2.1.1...HEAD
[2.1.1]: https://github.com/zfl4wless/sc2am/releases/tag/v2.1.1
[2.1.0]: https://github.com/zfl4wless/sc2am/releases/tag/v2.1.0
[2.0.1]: https://github.com/zfl4wless/sc2am/releases/tag/v2.0.1
[2.0.0]: https://github.com/zfl4wless/sc2am/releases/tag/v2.0.0
[1.4.1]: https://github.com/zfl4wless/sc2am/releases/tag/v1.4.1
