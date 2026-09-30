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
- [ ] Run `flake8 sc2am tests`.
- [ ] Run `python -m build` and inspect the generated artifacts.
- [ ] Verify the package metadata reports the intended version.
- [ ] Review `git diff` and confirm the working tree contains only release files.

## Publish

- [ ] Commit the release changes with a message such as
      `chore: prepares release v1.5.0`.
- [ ] Push the commit to `main` and wait for CI to pass.
- [ ] Create and push an annotated tag matching the package version, for example:
      `git tag -a v1.5.0 -m "Release v1.5.0"` and `git push origin v1.5.0`.
- [ ] Create a GitHub release for the tag and copy the matching changelog
      section into the release notes.
- [ ] Confirm the release assets and published version are visible.

## After publishing

- [ ] Add a new empty `Unreleased` section if the release process removed it.
- [ ] Verify installation from the published artifact in a clean environment.
- [ ] Announce the release with the user-facing changes and upgrade notes.

Never reuse a published version or tag. If a release must be corrected, bump
the version according to Semantic Versioning and document the correction.
