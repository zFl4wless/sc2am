# GitHub presentation review

Supports [#92](https://github.com/zFl4wless/sc2am/issues/92). Checked against
GitHub on **2026-10-08**, after v2.1.0 publication. Repository changes are
reviewable in the PR; external metadata proposals below require owner approval
before application. No repository settings were changed by this review.

## Reviewed surfaces

| Surface | Observed state | Review / proposed action |
| --- | --- | --- |
| About description | `Automate downloading SoundCloud tracks and importing them to Apple Music` | Replace with the copy below to name Mac users and existing playlists. Pending approval. |
| Topics | `apple-music`, `automation`, `downloader`, `macos`, `python`, `soundcloud` | Retain this relevant set. No CarPlay-only, Windows/Linux, lossless or catalog-matching topic is warranted. |
| Social preview | GitHub-generated image; `usesCustomOpenGraphImage: false` | Retain the generated preview; review the About copy separately. No custom graphic is needed for this focused change. |
| README badges | No CI or release badges before this change | Add main-branch CI and latest published release badges; neither claims live Apple/device verification. |
| Release / install target | Published stable v2.1.0, with uploaded wheel and sdist | Keep the installation pinned to the v2.1.0 wheel; link the release badge to GitHub's latest release. |
| Demo | Existing 36-second animated film and separate device record | Reuse both; disclose animation and evidence limits next to the demo link. |

The existing [film poster](demo/product-film/poster.png) was visually reviewed.
It introduces a SoundCloud track, but does not show the Apple Music destination;
using it as the repository's custom preview would weaken the new positioning.
Keep it as the demo thumbnail. If a custom preview is requested later, its copy
should be **“SC2AM — SoundCloud tracks in your Apple Music playlists”** with
**“For Mac · Local file import · Apple-managed iPhone sync”**, using the existing
film's visual style. Review the actual asset and its crop before uploading;
no such asset or new device footage is claimed here.

## Ready-to-review About copy

> Bring eligible SoundCloud tracks into your existing Apple Music playlists on Mac. Import tagged MP3s locally; use Apple's sync features for iPhone listening.

Apply only after the owner approves this exact description. Keep the six topics
above and the generated preview. This approval is separate from merging the
documentation PR. Check the resulting About text and shared-link preview after
application; preview caches may lag.

## Badge and evidence targets

- CI image: the existing `pull-request-ci.yml` workflow, explicitly scoped to
  `main`; its link opens that workflow filtered to main. A green main badge is
  not the status of the documentation PR's head commit.
- Release image: Shields' GitHub release badge for `zFl4wless/sc2am`; its link
  opens [the latest published release](https://github.com/zFl4wless/sc2am/releases/latest).
  At review, this resolves to [v2.1.0](https://github.com/zFl4wless/sc2am/releases/tag/v2.1.0).
- The published installation asset is `sc2am-2.1.0-py3-none-any.whl`; the release
  also contains `sc2am-2.1.0.tar.gz`. Neither badge establishes cloud upload,
  iPhone download, offline playback or CarPlay success.

#92's README work and metadata review can be reviewed now. The proposed About
change remains pending; keep #92 and its [roadmap](https://github.com/zFl4wless/sc2am/issues/94)
item open until the owner resolves it. On 2026-10-08 the owner dropped the
3–5-user pilot (#89) to keep the next phase lightweight. The next objective is
visibility and 16+ GitHub stars, not a scheduled research program. Stars measure
interest and do not establish successful use. Broader outreach still requires
separate approval; the existing demo and honest setup guide support it.

## Short launch draft — not published

> Keep eligible SoundCloud finds in your existing Apple Music playlists.
> SC2AM is a small Mac command-line tool that imports tagged MP3s into Music.app;
> Apple's sync features handle the iPhone path. Watch the
> [36-second animated demo](https://github.com/zFl4wless/sc2am/blob/main/docs/demo/product-film/sc2am-product-film.mp4)
> and follow the [setup and installation guide](https://github.com/zFl4wless/sc2am#end-user-installation-on-macos).
> If this is useful to you, a [GitHub star](https://github.com/zFl4wless/sc2am) supports the project.

One short demo post is the proposed next step after presentation review. Choose
a suitable audience and check its current posting rules before publication;
no community post or invitation has been sent. The 16+ star objective is not a
promised outcome.
