# GitHub project presentation

Supports [#92](https://github.com/zFl4wless/sc2am/issues/92). Reviewed on
**2026-10-08**, after v2.1.0 publication.

The README and repository metadata should help Mac users understand the supported
workflow, find installation instructions and distinguish local Music.app import
from Apple-managed synchronization.

## Repository metadata

The current About description is:

> Bring eligible SoundCloud tracks into your existing Apple Music playlists on Mac. Import tagged MP3s locally; use Apple's sync features for iPhone listening.

Relevant topics are `apple-music`, `automation`, `downloader`, `macos`, `python`
and `soundcloud`. These describe the supported workflow; avoid topics that imply
Windows/Linux support, lossless conversion or guaranteed catalog matching.

The repository uses GitHub's generated social preview. The existing
[film poster](demo/product-film/poster.png) introduces a SoundCloud track and
remains the demo thumbnail. Any future custom preview should make the Mac and
Music.app destination clear and be checked at its displayed crop and size.

## README and evidence links

- Keep the supported platform, Python/FFmpeg prerequisites, installation link,
  sync guide and demo easy to find near the opening.
- Link the existing main-branch CI badge to `pull-request-ci.yml`, filtered to
  `main`. Its status describes automated checks, not live Apple-device testing.
- Link the release badge to
  [the latest published release](https://github.com/zFl4wless/sc2am/releases/latest).
  The documented installation currently uses the published v2.1.0 wheel.
- Reuse the 36-second animated film and separate device acceptance record.
  Keep the animation and evidence limits visible next to the demo link.
- Explain that SC2AM confirms local import and playlist membership. Cloud
  availability, iPhone synchronization and catalog matching are separate.

## Short workflow introduction

> Keep eligible SoundCloud finds in your existing Apple Music playlists.
> SC2AM is a small Mac command-line tool that imports tagged MP3s into Music.app;
> Apple's sync features handle the iPhone path. Watch the
> [36-second animated demo](https://github.com/zFl4wless/sc2am/blob/main/docs/demo/product-film/sc2am-product-film.mp4)
> and follow the [setup and installation guide](https://github.com/zFl4wless/sc2am#end-user-installation-on-macos).

When sharing the project, choose a relevant audience, follow its posting rules
and disclose the project affiliation. Answer existing questions with accurate
setup guidance, and use actionable feedback to improve documentation or
reliability.
