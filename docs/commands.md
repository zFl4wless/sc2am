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

## Run the CLI Locally
Use the CLI entry point directly during development.

```bash
python main.py --help
python main.py config show
python main.py download "https://soundcloud.com/artist/track"
python main.py download "https://soundcloud.com/artist/track1" "https://soundcloud.com/artist/track2"
python main.py download "https://soundcloud.com/artist/track1" "https://soundcloud.com/artist/track2" --continue-on-error
```

The installed `sc2am` command is equivalent to `python main.py` and is used in
the examples in the README. Both `download` and `batch` also support
`--playlist NAME`, `--open` / `--no-open`, `--continue-on-error` /
`--stop-on-error`, and `--dry-run`.

Use `--dry-run` to validate URLs and preview the workflow without downloading,
writing files, creating log files, or accessing Music.app. To disable all Music
actions during a normal run, combine `--no-open --playlist ""`.

## Exit Codes

SC2AM uses stable exit codes for scripts and automation:

| Code | Meaning |
| --- | --- |
| `0` | Help, configuration, or processing completed without input/download failures |
| `1` | Runtime/setup or download failure, including a continued partial failure |
| `2` | Invalid CLI/configuration input or URL-validation abort |

Music.app open and playlist failures are reported as warnings and do not change
the exit code. See the [CLI and configuration contract](cli-and-config-contract.md)
for the complete precedence and validation rules.

## Build a Release Check
If packaging changes or a release is being prepared, verify the package metadata and build artifacts.

```bash
python -m build
```

## Release Workflow Summary
1. Merge the milestone work into `main`.
2. Bump version numbers in `pyproject.toml` and `sc2am/__init__.py`.
3. Run the test suite.
4. Create a Git tag such as `v1.2.0`.
5. Publish the GitHub release with release notes.
