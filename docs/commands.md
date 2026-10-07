# Commands

This file lists the most useful commands for developing, testing, and releasing SC2AM.

For the public commands, settings, precedence, validation rules, and exit codes,
see the [CLI and configuration contract](cli-and-config-contract.md).

## Environment Setup
Create and activate a virtual environment, then install development dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`pyproject.toml` is the dependency source of truth. The requirements files are thin wrappers for compatibility.

## Run the Test Suite
Run tests from the repository root with the project root on `PYTHONPATH`.

```bash
PYTHONPATH=. pytest -q
```

## Format Code
Format Python files with Black.

```bash
black sc2am main.py tests
```

## Lint Code
Run Flake8 on the application and tests.

```bash
flake8 sc2am main.py tests
```

## Audit Runtime Dependencies
Resolve and scan the runtime dependencies declared by `pyproject.toml`:

```bash
python -m pip install pip-audit
python -m pip_audit --strict .
```

This project-path audit excludes development extras. It checks the versions a
fresh installation resolves; use the upgrade instructions in the README for an
existing environment, where installed transitive versions may otherwise remain
unchanged.

## Run the CLI Locally
Use the CLI entry point directly during development.

```bash
python main.py --help
python main.py doctor
python main.py config show
python main.py download "https://soundcloud.com/artist/track"
python main.py download "https://soundcloud.com/artist/track1" "https://soundcloud.com/artist/track2"
python main.py download "https://soundcloud.com/artist/track1" "https://soundcloud.com/artist/track2" --continue-on-error
```

The installed `sc2am` command is equivalent to `python main.py` and is used in
the examples in the README. Both `download` and `batch` also support
`--playlist NAME`, `--open` / `--no-open`, `--continue-on-error` /
`--stop-on-error`, `--strict-import`, and `--dry-run`.

Use `--dry-run` to validate URLs and preview the workflow without downloading,
writing files, creating log files, or accessing Music.app. To disable all Music
actions during a normal run, combine `--no-open --playlist ""`.
Both commands accept `https://on.soundcloud.com/<token>` share links and resolve
them to a single track before processing. This also makes bounded HTTP requests
in `--dry-run`; use a direct SoundCloud track URL for offline URL validation.

## Repeat or Resume an Import

Rerun the same `download` or `batch` command with the same download directory.
An unchanged recorded MP3 is reused without network extraction, downloading or
retagging. Music checks the active library reference and playlist membership
before doing more work. A failed playlist stage can resume using the library
track. Pending mutations are reconciled by reads; unresolved ones stop with a
warning. Keep `.sc2am/history.sqlite3` alongside the downloads, and follow the
[isolated Music validation/recovery procedure](music-import-validation.md) if
manual reconciliation is needed. The summary includes reused downloads and
confirmed local Music results.

## Exit Codes

SC2AM uses stable exit codes for scripts and automation:

| Code | Meaning |
| --- | --- |
| `0` | Help, configuration, or processing completed without input/download failures |
| `1` | Runtime/setup or download failure, including a continued partial failure |
| `2` | Invalid CLI/configuration input or URL-validation abort |

`sc2am doctor` reports the platform and Python version, installed yt-dlp,
`ffmpeg`/`ffprobe` availability, download-directory accessibility, and basic
Music.app prerequisites. It returns `0` when all checked prerequisites are
available and `1` when a check fails (including invalid configuration). It
does not create files or logs, download anything, invoke Music.app, or modify
the library. Music.app presence and the `osascript` executable do not prove
that macOS automation permissions are granted or that a later Music operation
will succeed; those checks are intentionally not exercised.

Music.app import and playlist failures are warnings and do not change the exit
code by default. Use `sc2am download URL --strict-import` (also supported by
`batch`) to return `1` for failed/unconfirmed Music stages. Combine with
`--continue-on-error` to process remaining tracks after a Music failure.
Summaries separate downloads, confirmed imports and playlist results, including
partial success. Dry runs report previews only; local Music confirmation does
not verify cloud/iPhone availability. See the
[CLI and configuration contract](cli-and-config-contract.md)
for the complete precedence and validation rules.

## Build a Release Check
If packaging changes or a release is being prepared, verify the package metadata and build artifacts.

```bash
python -m build
```

See [`releasing.md`](releasing.md) for the complete release checklist and
[`../CHANGELOG.md`](../CHANGELOG.md) for the changelog format and current
release history.

## Release Workflow Summary
1. Review the release scope and update `CHANGELOG.md`.
2. Bump the version in `pyproject.toml` and `sc2am/__init__.py`.
3. Run the tests, lint, formatting, and package build checks.
4. Commit and push the release from `main`.
5. Create a matching tag such as `v1.5.0`.
6. Publish the GitHub release using the matching changelog section.
