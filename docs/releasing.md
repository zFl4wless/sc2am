# Release Checklist

Use this checklist for every SC2AM release. Start from the current `origin/main`
with no unrelated tracked changes, then prepare a `chore/` release branch and PR.
Preserve unrelated untracked files and exclude them from staging and artifacts.
Preparation and passing CI do not authorize tagging or publication.

## Prepare

- [ ] Review merged pull requests and open issues for the release scope.
- [ ] Collect verified changes since the last release in a candidate version
      section marked `Unreleased`; record the actual date only when publishing.
- [ ] Choose the next Semantic Versioning number:
      patch for fixes, minor for compatible features, major for breaking changes.
- [ ] Update the version in both `pyproject.toml` and `sc2am/__init__.py`.
- [ ] Confirm user-facing documentation and dependency metadata are current.

## Validate

- [ ] Run `PYTHONPATH=. pytest -q`.
- [ ] Run `black --check .`.
- [ ] Run `flake8 main.py sc2am tests scripts`.
- [ ] Run `mypy main.py sc2am`.
- [ ] Run `python -m pip_audit --strict .` against runtime dependencies.
- [ ] Run `python -m build` and `python scripts/verify_package_metadata.py dist` to
      verify the sdist and wheel license metadata and files.
- [ ] Verify the package metadata reports the intended version.
- [ ] Install each built format in a fresh virtual environment, run `pip check`,
      and run `scripts/smoke_installed.py` with `-I` from outside the checkout
      (see the commands below).
- [ ] Complete the [manual Music-to-iPhone release acceptance
      checklist](release-acceptance.md); record `NOT TESTED` where no live
      observation was made.
- [ ] Review `git diff` and the explicitly staged files; confirm only the focused
      release scope is committed and unrelated files are unchanged/excluded.

## Review and merge

- [ ] Commit the release changes with a message such as
      `chore: prepares release v1.5.0`.
- [ ] Push the release branch, open a review-ready PR using the repository
      template, and wait for all CI jobs on the final pushed commit to pass.
- [ ] Obtain the required approval from a reviewer other than the PR author;
      merge through the protected `main` workflow without bypassing its rules.

## Publish (after merge and explicit approval)

- [ ] Obtain explicit approval to publish the merged release candidate.
- [ ] Revalidate the final `main` commit, version agreement and release artifacts;
      ensure its CI passed and the acceptance evidence applies to its code.
- [ ] Set the actual release date in the changelog through a reviewed change and
      update candidate/install links to the intended release; revalidate that
      final commit before tagging. Do not advertise nonexistent assets as current.
- [ ] Create and push an annotated tag matching the package version, for example:
      `git tag -a v1.5.0 -m "Release v1.5.0"` and `git push origin v1.5.0`.
- [ ] Wait for CI on the tag's final commit to pass before creating the release.
- [ ] Create a GitHub release for the tag and copy the matching changelog
      section into the release notes.
- [ ] Confirm the release assets and published version are visible.
- [ ] Close the shipped release milestone and update the roadmap only after
      publication. Record superseded versions as skipped, never as releases.

## After publishing

- [ ] Add a new empty `Unreleased` section if the release process removed it.
- [ ] Verify installation from the published artifact in a clean environment.
- [ ] Announce the release with the user-facing changes and upgrade notes.

Never reuse a published version or tag. If a release must be corrected, bump
the version according to Semantic Versioning and document the correction.

For the v2.1.1 candidate, see [v2.1.1 release notes](releases/v2.1.1.md)
and its [manual acceptance record](releases/v2.1.1-acceptance.md). Set its actual
publication date and update README/dependency-install links when publication is
ready; until assets are visible, the documented end-user wheel remains v2.1.0.
For v2.1.0, see [v2.1.0 release notes](releases/v2.1.0.md).
The planned v2.0.2 scope is included in v2.1.0; no v2.0.2 tag or release is
created. Milestones #8 and #9 must remain open until publication is verified.

## Fresh artifact installation

After building and verifying `dist`, run from the repository root with the
development environment active. Use a new temporary directory for each run:

```bash
release_root=$(pwd)
release_check=$(mktemp -d)
for artifact in "$release_root"/dist/*.whl "$release_root"/dist/*.tar.gz; do
  artifact_name=$(basename "$artifact")
  artifact_venv="$release_check/$artifact_name-venv"
  python -m venv "$artifact_venv"
  "$artifact_venv/bin/python" -m pip install "$artifact" || exit 1
  "$artifact_venv/bin/python" -m pip check || exit 1
  (cd "$release_check" && "$artifact_venv/bin/python" -I \
    "$release_root/scripts/smoke_installed.py") || exit 1
done
```

The smoke script checks agreement between the installed metadata and module
version. Separately compare both to `pyproject.toml` and the intended release
number; agreeing on an old version is not a successful release check.

## Automated checks

CI runs on pull requests, pushes to `main`, and release tags matching `v*`.
The Ubuntu test/lint/format matrix retains Python 3.10 and 3.12 coverage and
includes `main.py` in linting. Package jobs build an sdist and a wheel, then
install each format in a fresh virtual environment on Ubuntu. macOS also builds
and installs the wheel and runs the same CLI smoke check.

Package jobs verify that both artifact formats declare the SPDX license
expression and include the license file. `scripts/smoke_installed.py` must run
with the installed environment's Python using `-I`, from outside the checkout.
It verifies installed module paths,
entry-point metadata and version agreement, help, configuration initialization
and display, download/batch dry runs, invalid-input exit status, and absence of
download/log writes. On macOS it also executes a harmless `osascript` command.
These checks need no SoundCloud connection, FFmpeg, personal Apple account, or
Music library. Actual Music imports and Automation permissions still require
manual verification using [the macOS setup checklist](macos-setup.md).
