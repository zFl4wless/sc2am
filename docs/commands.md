# Commands

This file lists the most useful commands for developing, testing, and releasing SC2AM.

## Environment Setup
Create and activate a virtual environment, then install development dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

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
```

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

