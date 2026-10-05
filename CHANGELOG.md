# Changelog

All notable user-facing changes to SC2AM are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases use [Semantic Versioning](https://semver.org/).

## [Unreleased]

Changes merged after the latest release will be collected here until the next
release is prepared.

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

[Unreleased]: https://github.com/zfl4wless/sc2am/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/zfl4wless/sc2am/releases/tag/v2.0.1
[2.0.0]: https://github.com/zfl4wless/sc2am/releases/tag/v2.0.0
[1.4.1]: https://github.com/zfl4wless/sc2am/releases/tag/v1.4.1
