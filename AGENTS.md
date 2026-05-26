# AGENTS.md

## Purpose
SC2AM automates downloading SoundCloud tracks and importing the resulting MP3s into Apple Music on macOS.
When working in this repository, prefer small, well-tested changes that keep the CLI behavior predictable for end users.

## Project Map
- `main.py`: Click-based CLI entry point and command wiring.
- `sc2am/validator.py`: URL validation and batch file validation.
- `sc2am/downloader.py`: yt-dlp integration, download flow, and download error classification.
- `sc2am/metadata.py`: metadata normalization, ID3 tagging, and cover-art embedding.
- `sc2am/apple_music.py`: macOS Music.app integration.
- `sc2am/config_manager.py`: configuration loading, defaults, and environment overrides.
- `tests/`: unit tests for validation, config defaults, error messages, and metadata mapping.

## Working Principles
1. Prefer the smallest change that solves the issue.
2. Do not introduce hard-coded environment-specific values.
3. Keep user-facing errors clear, actionable, and stable.
4. Preserve backwards compatibility unless the task explicitly asks for a breaking change.
5. Update tests whenever behavior changes.
6. Keep repository docs aligned with code changes.

## Default Workflow
1. Read the relevant implementation and tests before editing.
2. Identify the code path end-to-end, not just the local function.
3. Make the code change.
4. Add or update tests that prove the behavior.
5. Run the test suite before considering the task done.
6. Check for obvious regressions in docs or release metadata when relevant.

## Verification Standard
- Run `PYTHONPATH=. pytest -q` after functional changes.
- If the task affects packaging or release behavior, also validate `pyproject.toml` and version metadata.
- If a change touches the CLI, confirm the user-facing message is understandable without reading logs.

## Release Tasks
When preparing a release:
- Bump the version in `pyproject.toml` and `sc2am/__init__.py` together.
- Re-run tests before tagging.
- Use a release tag that matches the version number, for example `v1.2.0`.
- Write release notes that summarize user-facing changes, not internal implementation details only.

## Documentation Expectations
If behavior changes in a user-visible way, update at least one of:
- `README.md`
- `docs/architecture.md`
- `docs/commands.md`
- `.github/pull_request_template.md`

## Good Agent Behavior
- Ask for clarification only when the repository context is insufficient.
- Do not guess about file formats or platform behavior when existing code can be inspected.
- Prefer direct verification over assumptions.
- Leave the codebase cleaner and easier to understand than before.

