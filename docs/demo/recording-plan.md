# SoundCloud → Music → iPhone → CarPlay demo preparation

For [issue #88](https://github.com/zFl4wless/sc2am/issues/88), based on main
`2e5b46963548c903eb99f25f01db9857a068f19a`. Prepared on 2026-10-08.

**Status: RECORDING PENDING. No demo video has been recorded or published.**
The owner has authorized use of the existing SC2AM test Music library and
publication of sanitized demo footage; the personal Mac library is excluded.
UI inspection confirmed the test playlist/fixtures, an isolated test media
folder and Sync Library disabled. A real download/import, repeated import and
repeated-URL batch passed in that local test library. Tags and artwork were
verified in the MP3 and Music.app; see the [dated acceptance record](device-acceptance-2026-10-08.md).
The authorized new cloud-test library subsequently showed `Uploaded`; the dated
record includes the observed wait and screenshot. The owner reports successful
iPhone appearance, download and offline playback; no independent device
observation or iPhone/CarPlay footage has been supplied. The owner also confirms
successful real wireless CarPlay playback in a BMW, including the offline check.
Extended local same-title, Unicode/quoted-playlist, actual Automation-denial and
controlled transfer-interruption/retry tests also passed using a separate looped
20-minute source. This source was tested only in the nonsynced local library.
The checked-in captions are an editing draft, not evidence.

## Source choice and recording status

- The proposed [City Lights Drive](https://soundcloud.com/fl4wless-167171478/city-lights-drive)
  page was verified as a public single track by fl4wless. The owner reports that
  both audio and cover were generated with ElevenMusic Website Free. This is
  not documented as a self-recorded composition.
- Under the [ElevenMusic terms](https://elevenmusic.io/terms-of-use), updated
  2026-09-11 and checked 2026-10-08, a Free-generated New Song can be used in
  commercial media with prominent `Made with ElevenMusic` attribution, but
  release through digital streaming platforms is limited to songs created under
  Pro. The current Free-generated SoundCloud source is therefore not cleared
  for this demo workflow. No audio or cover was downloaded, imported or recorded;
  the owner's upload was not changed or deleted.
- A replacement source package, `Midnight Circuit` (Electronic; suggested tags:
  synthwave, instrumental), was prepared locally: a new
  32-second stereo synth recording and geometric cover, plus generator and
  provenance/hashes. It uses mathematical oscillators/noise, no sampled
  recordings or music-generation service. The original geometric artwork was
  edited with OpenAI ImageGen to remove all text; the package records that
  provenance. Source assets are not demo evidence.
  The owner uploaded the replacement as a public single
  [SoundCloud track](https://soundcloud.com/fl4wless-167171478/midnight-circuit)
  with the expected title, creator, genre, tags and text-free artwork.
- The existing test library is not cloud-synced and must remain that way. The
  owner expressly authorized a new, initially empty Mac test library connected
  to their personal Apple Music account, uploading only `Midnight Circuit`.
  Personal cloud items must not be modified, recorded or published. This is a
  documented exception to the disposable-account recommendation, not isolated
  cloud-account testing. With owner assistance for Option-launch, the new
  library was created, verified empty and given only the demo track before
  enabling sync. It reached `Uploaded` (first observed after 48.539 seconds;
  actual completion may be earlier between checks). The owner confirms iPhone
  appearance, download and offline playback; the exact appearance time and raw
  phone footage are missing. The owner confirms the parked wireless BMW CarPlay
  test, including audible offline playback; raw CarPlay footage is still missing.
  No Finder transfer has been tested.

Issue #87 is closed and provides the [manual release acceptance
checklist](../release-acceptance.md). Its existence does not prove live device
results. Earlier [local import evidence](../music-import-validation.md) covers a
different run and does not establish this demo's iPhone/CarPlay journey.

## Prerequisites for the recording

- Follow the [macOS setup guide](../macos-setup.md) and [contributor
  installation](../../README.md#contributor-setup). Record the tested commit or
  release, Python/yt-dlp/FFmpeg versions, macOS/Music versions and Mac model.
  FFmpeg and ffprobe must be available, with Music Automation permission granted.
- Use a disposable macOS user and isolated Music library/media/download folders.
  A custom SC2AM config isolates downloads; it does **not** select a Music
  library. Verify the active library before any live command.
- Obtain explicit authorization for the chosen test library, test Apple Account,
  iPhone and vehicle, including recording and public use of sanitized footage.
  Do not inspect personal libraries or account/device content to fill gaps.
- For the planned cloud route, use an authorized test Apple Account with Apple
  Music or iTunes Match, the same account on the test Mac/iPhone, Sync Library
  enabled and internet access. Record iOS version/model and available storage.
  Follow the existing setup guide; do not change a personal library's sync mode.
- Use a compatible CarPlay vehicle/head unit with its supported wired/wireless
  connection, parked for recording. Record vehicle/head unit and connection type.
- Select one downloadable SoundCloud track with verified permission for download,
  device transfer and public audiovisual use, plus permission to display its
  artwork. Prefer a track and cover owned by the recorder. Record the canonical
  track URL, creator, license/permission evidence and required credit first.

## Audio, artwork and attribution

No audio or cover image is included in this preparation. Do not use arbitrary
SoundCloud audio, or assume the project's MIT license covers it.

An optional music candidate is [Discovery by Scott
Buckley](https://soundcloud.com/scottbuckley/discovery-cc-by). On 2026-10-08,
the creator's [track page](https://www.scottbuckley.com.au/library/discovery/)
identified the music as CC BY 4.0. His [usage
page](https://www.scottbuckley.com.au/library/using-this-music/) specifies
attribution in the YouTube description and excludes standalone resale and
reuploads to music streaming platforms. The [license
deed](https://creativecommons.org/licenses/by/4.0/) requires credit, a license
link and disclosure of changes. This music-only review does not clear its
SoundCloud artwork or confirm permissions for the proposed cloud route; resolve
those before choosing it. An owned track/cover avoids these unresolved items.

For that candidate, the proposed credit is:

> 'Discovery' by Scott Buckley — released under CC-BY 4.0.
> www.scottbuckley.com.au

Add the track-page and license links to the final video description and companion
README text. State actual edits (for example, excerpted, MP3 conversion, fades)
and credit the cover separately. Do not publish the credit as if audio had
already been used. For another track, replace it with the verified rights
holder's required credit and links. Keep the permission record with the evidence.

## Command verification

The first command tested for this task was a **dry run** on 2026-10-08, from the
repository root with Python 3.14.8. A temporary config contained
`download_dir: <temporary-test-root>/downloads` and `log_file: null`.
Inherited `SC2AM_*` environment overrides were removed from the test subprocess.
`<temporary-test-root>` below replaces the generated temporary path only:

```bash
.venv/bin/python main.py --config "<temporary-test-root>/config.yaml" \
  download "https://soundcloud.com/artist/track" \
  --open --playlist "" --stop-on-error --strict-import --dry-run
```

Observed stdout:

```text
Track: Validating SoundCloud URL...
Track: OK: Valid SoundCloud URL
Track: DRY-RUN: Would download track
Track: DRY-RUN: Would import into Apple Music
Track: DRY-RUN complete (no changes made)
Dry-run previews: 1 succeeded, 0 failed (100% success rate)
DRY-RUN: No downloads, imports or playlist changes performed.
```

Exit code was 0, stderr was empty, and the download directory was not created.
This placeholder URL passes local syntax validation only. Its existence, audio,
tags, artwork, Music import and device playback were **NOT TESTED**.

The later [live local acceptance run](device-acceptance-2026-10-08.md) tested the
actual `Midnight Circuit` URL successfully, including confirmed Music import.
It produced logs and screenshots, not a demo video. A separate later cloud
upload and the owner's iPhone test report are documented in the same record;
CarPlay is also owner-confirmed; device video evidence remains pending.

For the future video recording, create a config pointing at the isolated download
directory, remove inherited `SC2AM_*` overrides, replace the URL with the
rights-cleared track and use the following command structure. This placeholder
form is a proposal; the dated record contains the actual tested invocation:

```bash
.venv/bin/python main.py --config "/path/to/isolated-demo/config.yaml" \
  download "https://soundcloud.com/REPLACE_CREATOR/REPLACE_TRACK" \
  --open --playlist "" --stop-on-error --strict-import
```

The empty playlist disables inherited playlist actions; `--open` requests local
import and `--strict-import` makes an unconfirmed import fail. Neither option
confirms cloud sync or playback. Record the exact successful command, selected
config, sanitized stdout/stderr and exit code; replace this proposal with that
tested command in the published companion text. Keep MP3 and journal together.

## Storyboard and shot list — target 55 seconds

This is an edit plan for real footage, not a simulated walkthrough. Shoot all
stages with the same track and retain the raw evidence. The caption draft in
[captions.en.vtt](captions.en.vtt) doubles as the optional narration script;
update its timings and bracketed fields after reviewing the footage.

| Edit time | Shot to capture | Evidence and on-screen disclosure |
| --- | --- | --- |
| 00–05 | Title/setup card with chosen route and test versions | Caption: isolated library; subscription and Sync Library for this route. Link full prerequisites in the description. |
| 05–13 | Terminal: paste the real SoundCloud URL, execute the live command, show stage summary | Large text, URL/command readable. If download time is removed, label `Download/import cut: [actual elapsed time]`. Keep full log. |
| 13–21 | Music.app: the imported song and its Details/Artwork panes | Show actual title, artist and artwork; verify embedded MP3 tags/artwork separately. Crop to test content. Never paste artwork over Music's UI. |
| 21–28 | Mac Cloud Status before/after, with a transition card for the omitted wait | Display observed status and `Cloud wait: [measured duration]; cut`. Record first import, Matched/Uploaded and first iPhone appearance times. A cut must not suggest instant synchronization. |
| 28–37 | Test iPhone Music library: find the same track, show download completion and start playback | Actual phone capture; show title/artist/cover. Only claim offline playback after observing it with both Wi-Fi and cellular data disabled. Retain that evidence. |
| 37–48 | Real CarPlay Music screen: select the track, press play, show advancing elapsed time and capture audible playback | Film in a parked vehicle. Keep sound captured from the real playback; do not replace it with an added soundtrack as proof. Label the device/vehicle transition as a cut. |
| 48–55 | Credits and scope card | Music/cover credit and source/license links in description. Disclose every omitted/untested step and the tested command. |

If Finder is the tested route, replace the cloud shot and cloud/subscription
captions with the actual Finder transfer and measured duration; say `Finder sync`
throughout. Do not depict a cloud test. Follow the setup guide's device-content
replacement precautions. If offline playback is untested, remove that claim and
label it `Offline playback: NOT TESTED`. If any core shot is missing, retain the
preparation status instead of publishing a complete-journey claim.

## Readability and edit rules

- Export a 30–60 second 1080p video with burned-in captions and a matching VTT
  sidecar. Aim for 55 seconds. Use at most two short caption lines, high contrast,
  approximately 48 px at 1080p, and enough dwell time to read them.
- Crop/zoom terminal and device screens without hiding the verification context;
  preview at README/mobile viewing size, with sound off as well as on.
- Mark cuts, speed changes and measured cloud waits on screen where they occur.
  Do not fill a long wait with invented success output or animated fake devices.
- The VTT contains draft-only notes and placeholders. Replace measured fields,
  remove unsupported statements and align captions to actual footage before
  export. No draft caption is a passed test.
- Hide account names, emails, notifications, personal paths, unrelated tracks,
  vehicle identifiers and people; retain only authorized test content. Review
  every frame and the captured audio before public upload.

## Concrete recording handoff

Source rights, the authorized libraries/devices and the actual test commands
are recorded in the [dated acceptance record](device-acceptance-2026-10-08.md).
Use the **32-second** [Midnight Circuit source](https://soundcloud.com/fl4wless-167171478/midnight-circuit)
for the final demo; the separate 20-minute loop is for local acceptance only.
No further source upload is needed.

Retain uncut raw files for each of these shots, then edit the 55-second plan:

1. **Mac terminal (10–15 seconds):** large readable text; paste the actual short
   source URL and run the live command below. Keep validation, verified-download
   reuse/download and confirmed-import output visible. This already imported
   track will normally be reused; label that honestly instead of presenting it
   as a first download. Confirm the authorized local library before running.
2. **Mac Music (10–15 seconds):** the short track's Details and Artwork panes.
   Show title, artist, genre and the actual cover. Exclude the account sidebar,
   private paths and unrelated tracks. The checked-in still images are reference
   evidence, not motion footage.
3. **Cloud transition:** the original upload was observed but not filmed. Either
   record a new authorized transfer with new measured timestamps, or use the
   actual Uploaded still with `Earlier Mac observation; upload not filmed`.
   Label `First observed Uploaded after 48.539 s; wait omitted; phone arrival
   time unknown`. Do not animate it into a fake live upload or re-enable sync
   for the old fixture library. Switching libraries requires owner assistance.
4. **iPhone (15–20 seconds):** start recording before finding the short track in
   Music. Show the downloaded state, correct cover and title. Disable Wi-Fi and
   cellular data in Settings, return to Music, restart from 0:00 and retain
   evidence of audible playback. A separate camera recording captures actual
   speaker audio reliably; do not assume screen recording includes Music audio.
   Hide notifications and unrelated library content.
5. **Parked BMW CarPlay (15–20 seconds):** film the real screen with a separate
   camera. Keep Wi-Fi/Bluetooth on for wireless CarPlay, cellular data off and
   no other internet route. Find the short track, press play and capture at least
   five seconds of advancing time and audible car-speaker playback. Do not add
   a soundtrack over this proof. Restore the phone's previous network settings
   afterward. Exact BMW model is optional context and remains unknown so far.

Save the raw footage in a local folder accessible to the editor and provide its
path. Public consent covers sanitized demo content; review every frame and its
sound before publishing. No account address, personal songs or vehicle identifier
is needed. Reports that the tests worked cannot substitute for these shots.

The actual tested short-track command is:

```bash
.venv/bin/python main.py --config "<demo-root>/config.yaml" \
  download "https://soundcloud.com/fl4wless-167171478/midnight-circuit" \
  --open --playlist "" --stop-on-error --strict-import
```

Run from the repository root with the virtual environment first on PATH and
inherited `SC2AM_*` overrides removed; use the existing isolated demo config.
The config selects downloads, **not** the Music library. Once raw recordings are
available, retime the captions, add actual-source credits, export 1080p with
burned-in captions plus VTT, check duration/readability/privacy and replace the
README's pending link with the reviewed real video. Keep the PR draft and #88
open until that export exists.

## Open acceptance criteria for #88

- [ ] Link input, tagged track/artwork in Music, iPhone availability and CarPlay
  playback shown in real footage — **OPEN / NOT TESTED for this demo**.
- [ ] Owned/authorized audio used and cloud waits/edits honestly labeled —
  **OPEN**: replacement source is cleared and Mac wait recorded; the final
  video and its truthful labels/credits are still pending.
- [ ] Readable captioned 30–60 second demo published with prerequisites and a
  tested live command — **OPEN**: storyboard/caption draft, actual tested live commands and
  acceptance evidence exist; captioned export and public video link are pending.

## README proposal once evidence is complete

Keep the current README's `recording pending` link until all three criteria have
evidence. Then replace that section with a real video link and the following
text, filling every bracket from the recorded run:

> Watch the [duration]-second captioned demo: [real hosted video link]. Recorded
> with SC2AM [release/commit], macOS/Music [versions], iOS [version] and [CarPlay
> vehicle/connection], using an isolated test library and [Sync Library/Finder].
> Prerequisites: [macOS setup link] and [subscription, if applicable]. Tested
> command: [exact live command]. [Measured cloud/transfer wait] was cut; [other
> edits]. Not shown: [steps]. Not tested: [steps or none, based on evidence].
> Music: [verified attribution/source/license]. Artwork: [verified credit].

Attach the final VTT, evidence record and sources next to that link; retain a
text transcript so the result is understandable without video/audio. Leave #88
open while footage is missing. Roadmap #94 is unchanged and must only be checked
after review and merge of completed work. This preparation creates no release
or tag and does not change the audit document.
