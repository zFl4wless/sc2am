# Release Checklist

Use this checklist for every SC2AM release. Complete it from a clean working
tree on the `main` branch.

## Prepare

- [ ] Review merged pull requests and open issues for the release scope.
- [ ] Move the relevant `CHANGELOG.md` entries from `Unreleased` into a new
      version section with the release date.
- [ ] Choose the next Semantic Versioning number:
      patch for fixes, minor for compatible features, major for breaking changes.
- [ ] Update the version in both `pyproject.toml` and `sc2am/__init__.py`.
- [ ] Confirm user-facing documentation and dependency metadata are current.

## Validate

- [ ] Run `PYTHONPATH=. pytest -q`.
- [ ] Run `black --check .`.
- [ ] Run `flake8 main.py sc2am tests scripts`.
- [ ] Run `python -m build` and inspect the generated artifacts.
- [ ] Verify the package metadata reports the intended version.
- [ ] Review `git diff` and confirm the working tree contains only release files.

## Publish

- [ ] Commit the release changes with a message such as
      `chore: prepares release v1.5.0`.
- [ ] Push the commit to `main` and wait for CI to pass.
- [ ] Create and push an annotated tag matching the package version, for example:
      `git tag -a v1.5.0 -m "Release v1.5.0"` and `git push origin v1.5.0`.
- [ ] Wait for CI on the tag's final commit to pass before creating the release.
- [ ] Create a GitHub release for the tag and copy the matching changelog
      section into the release notes.
- [ ] Confirm the release assets and published version are visible.

## After publishing

- [ ] Add a new empty `Unreleased` section if the release process removed it.
- [ ] Verify installation from the published artifact in a clean environment.
- [ ] Announce the release with the user-facing changes and upgrade notes.

Never reuse a published version or tag. If a release must be corrected, bump
the version according to Semantic Versioning and document the correction.

## Automated checks

CI runs on pull requests, pushes to `main`, and release tags matching `v*`.
The Ubuntu test/lint/format matrix retains Python 3.10 and 3.12 coverage and
includes `main.py` in linting. Package jobs build an sdist and a wheel, then
install each format in a fresh virtual environment on Ubuntu. macOS also builds
and installs the wheel and runs the same CLI smoke check.

`scripts/smoke_installed.py` must run with the installed environment's Python
using `-I`, from outside the checkout. It verifies installed module paths,
entry-point metadata and version agreement, help, configuration initialization
and display, download/batch dry runs, invalid-input exit status, and absence of
download/log writes. On macOS it also executes a harmless `osascript` command.
These checks need no SoundCloud connection, FFmpeg, personal Apple account, or
Music library. Actual Music imports and Automation permissions still require
manual verification using [the macOS setup checklist](macos-setup.md).
