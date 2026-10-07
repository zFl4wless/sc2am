# Manual Music-to-iPhone release acceptance

Use this checklist for the end-to-end path from a locally imported track to
iPhone, offline, and CarPlay playback. Automated tests and hosted CI do not
verify Apple Music, cloud sync, an iPhone, or a car. A passing local import is
not evidence that the track reached another device.

Complete one record for each release candidate. Use `PASS`, `FAIL`, `NOT TESTED`,
or `N/A` with a reason for every row. Keep sanitized screenshots, command output,
and test identifiers as evidence; exclude Apple Account details and personal
library content.

## Test record

| Field | Value |
| --- | --- |
| SC2AM release / commit |  |
| Tester and date |  |
| macOS version and Mac model |  |
| Music app version |  |
| iOS version and iPhone model |  |
| Apple Music or iTunes Match / Finder-only |  |
| CarPlay vehicle / connection type, if tested |  |
| Isolated test library and download directory |  |

## Safety and setup

- [ ] Use a disposable macOS user and test Music library. For Sync Library,
  use a test Apple Account, subscription, and iPhone; do not enable cloud sync
  for a personal library as part of this test.
- [ ] Confirm the test library is empty, its media folder and SC2AM download
  folder are isolated, and its Sync Library state matches the test route.
- [ ] Use tracks you have permission to download and test. Record their source
  URLs or sanitized IDs. Do not use private or personal library tracks.
- [ ] Confirm the account, phone, and car are online for setup. Record available
  free storage on the phone.
- [ ] For Finder sync, use a test phone/library and review any **Erase and Sync**
  prompt before proceeding; it replaces the selected content type on the phone.
- [ ] Do not treat a simulated response, mocked test, `doctor` result, or local
  Music reference as proof of cloud sync or device playback.

If a disposable account/device or a safe isolated library is unavailable, mark
the affected rows **NOT TESTED**. Do not switch Sync Library on or off in a
personal library to force a result; disabling it removes downloaded music from
the iPhone.

## Results

| Scenario | Status | Evidence / notes |
| --- | --- | --- |
| Downloaded MP3 has expected title, artist, and embedded artwork | NOT TESTED |  |
| Music.app confirms the imported track in the isolated Mac library | NOT TESTED |  |
| Two different tracks with the same title remain distinct and have correct metadata | NOT TESTED |  |
| Repeating a URL reuses the verified file and does not create a duplicate Music track | NOT TESTED |  |
| Batch input with a repeated URL also avoids duplicate tracks | NOT TESTED |  |
| Playlist name with commas, quotes, and Unicode imports into the intended playlist | NOT TESTED |  |
| Missing `ffmpeg` / `ffprobe` is reported clearly in a restricted test PATH | NOT TESTED |  |
| Missing Music Automation permission reports the failure and sends no import mutation | NOT TESTED |  |
| Interrupted network transfer fails safely; retry does not import a partial file or duplicate a track | NOT TESTED |  |
| A representative long track downloads and imports completely; duration and file size recorded | NOT TESTED |  |
| Sync Library: cloud status reaches Matched or Uploaded, then the track appears on the test iPhone | NOT TESTED |  |
| Sync Library: downloaded track plays on iPhone with Wi-Fi and cellular data disabled | NOT TESTED |  |
| Finder route: selected track syncs to the test iPhone and plays offline | NOT TESTED |  |
| CarPlay: Music finds and plays the track; offline playback works for a downloaded/synced copy | NOT TESTED |  |

For the cloud route, record whether Apple marks the track **Matched** or
**Uploaded**, and how long the update took. Do not set an expected immediate
sync time. If the file is over Apple's documented 200 MB cloud limit or the
library has reached 100,000 songs, record that condition and mark the cloud row
**N/A** only with the reason; the Finder route can be checked separately.

## Release decision

- [ ] All in-scope scenarios pass and have evidence; no required scenario is
  `FAIL` or `NOT TESTED`.
- [ ] Any `N/A` has a specific reason and does not hide an unmet release claim.
- [ ] `docs/macos-setup.md` and release notes describe only behavior verified by
  this record. If the live journey was not tested, say so plainly.

**Overall gate:** NOT TESTED  
**Reviewer and date:**

The gate is not a pass while a required row is `FAIL` or `NOT TESTED`. A local
test, mocked suite, or CI run cannot substitute for the iPhone and CarPlay
observations above. See [macOS setup and troubleshooting](macos-setup.md) for
the user workflow and [Music import validation](music-import-validation.md) for
the isolated local Music test scope.
