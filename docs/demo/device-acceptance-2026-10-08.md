# Device acceptance record — 2026-10-08 (in progress)

Supports [issue #88](https://github.com/zFl4wless/sc2am/issues/88) and the
[manual acceptance checklist](../release-acceptance.md). This is a real local
run with screenshots and logs, **not an end-to-end demo video**. The full
release gate is **NOT TESTED**. No release or tag was created.

## Environment and authorization

| Field | Value |
| --- | --- |
| Tested commit | `c87126d7310a298b0e1e3756c2e448d7b5d4d06b` (documentation branch; functional code from main `2e5b469`) |
| Tester / date | Codex-assisted Mac observations; owner device details; 2026-10-08 |
| Mac / macOS / Music | Mac14,2 / 27.0 / 1.7 |
| Python / yt-dlp / FFmpeg | 3.14.8 / 2026.7.4 / 9.0.2 |
| iPhone / iOS / free space | Owner reports iPhone 13 / 27.0.1 / approximately 20 GB; not independently observed |
| Subscription / phone sync | Owner reports Apple Music subscription and iPhone Sync Library already enabled |
| CarPlay | Owner reports wireless connection; vehicle/head-unit model still needed |
| Local library | Existing authorized SC2AM test library, ID `0EFDCF7D075BAF42`; isolated test media folder; Sync Library off |
| Download isolation | New dedicated demo directory, represented below by `<demo-root>`; custom config; inherited `SC2AM_*` removed |

The owner explicitly authorized the existing Mac test library and sanitized
public demo evidence, excluding the personal Mac library. It contained eight
older test tracks before this run; it was not empty and was not created under a
disposable macOS user. These exceptions are recorded, not marked as compliance
with the checklist's recommended empty/disposable setup.

After this local run, the owner expressly authorized a **new, initially empty**
Mac test library using the personal Apple Music account, uploading only
`Midnight Circuit`. Cloud library items may populate its view, but must not be
modified, recorded or published. This is not an isolated cloud account. The
existing local test library and its older fixtures must not be synchronized.
Creating the new library is pending owner assistance with Option-launch; no
cloud checkbox has been enabled. No phone sync settings were changed.

## Source and attribution

[Midnight Circuit by fl4wless](https://soundcloud.com/fl4wless-167171478/midnight-circuit),
SoundCloud track ID `2415115401`: original algorithmic audio generated locally
from oscillators/noise, no external samples or music-generation service. Original
geometric cover edited with OpenAI ImageGen to remove text. The owner uploaded
the prepared source package for this test. Source hashes and provenance are
retained with the local package. The earlier ElevenMusic Free track is not used.

Proposed public credit: **Midnight Circuit — original algorithmic demo audio,
created with Codex assistance; original geometric artwork, edited with OpenAI
ImageGen.** Link the SoundCloud source and disclose the actual excerpt/MP3
conversion and video cuts in the final demo. No final video has been edited.

## Actual local commands and observations

From the repository root, the following CLI invocation ran with the repository
virtual environment first on PATH and inherited `SC2AM_*` variables removed.
Only the dedicated generated directory is replaced by `<demo-root>` below.
Config: `download_dir: <demo-root>/downloads`, `default_playlist: null`,
`open_music_app: true`, `continue_on_error: false`, `log_level: INFO`,
`log_file: null`.

```bash
.venv/bin/python main.py --config "<demo-root>/config.yaml" \
  download "https://soundcloud.com/fl4wless-167171478/midnight-circuit" \
  --open --playlist "" --stop-on-error --strict-import
```

Started at 05:29:18.763 UTC; finished at 05:29:23.235 UTC; elapsed 4.472 seconds;
exit code 0; stderr empty. These are measured total download/import times,
**not cloud synchronization times**. Actual stdout:

```text
Track: Validating SoundCloud URL...
Track: OK: Valid SoundCloud URL
Track: Downloading track...
Track: OK: Downloaded: Midnight Circuit [2415115401].mp3 (metadata embedded)
Track: Importing into Apple Music...
Track: OK: Import confirmed in Apple Music
Track: Done!
Downloads: 1 succeeded, 0 failed (100% success rate)
Imports: 1 confirmed, 0 failed/unconfirmed
Playlists: not requested
Music confirmation covers the local library only; cloud/iPhone availability is not verified.
```

The MP3 is 834,948 bytes, 44,100 Hz and 32.078 seconds. Mutagen confirmed title
`Midnight Circuit`, artist `fl4wless`, album `SoundCloud`, genre `Electronic`
and one embedded JPEG cover. Its SHA-256 after SC2AM's import marker was added:
`6b7a3af2e461ee8f7b49b6224d34aca62edb33313548b902d0b3f15b77308400`.
Music.app displayed the same tags and artwork. The journal recorded Music track
ID `891EE6C629AA2506` in the test library.

![Actual imported track details in Music.app](evidence-2026-10-08/music-details.png)

![Actual imported text-free artwork in Music.app](evidence-2026-10-08/music-artwork.png)

The same command then ran again with exit 0, empty stderr and
`Reused verified download: Midnight Circuit [2415115401].mp3`.
A UTF-8 file contained the same URL on two lines. Actual batch invocation:

```bash
.venv/bin/python main.py --config "<demo-root>/config.yaml" \
  batch "<demo-root>/repeated-urls.txt" \
  --open --playlist "" --stop-on-error --strict-import
```

Batch exit 0, empty stderr, two verified file reuses and two confirmed import
operations. After both checks, Music's Songs view filtered to `Midnight Circuit`
contained exactly one row. These confirmation counts describe operations, not
new tracks. The screenshots are still images; no terminal/Music video was
recorded, and no local playback was claimed.

## Acceptance results

| Scenario | Status | Evidence / notes |
| --- | --- | --- |
| MP3 title, artist and embedded artwork | PASS | Actual file inspection and screenshots above |
| Music confirms imported track in isolated Mac library | PASS | CLI confirmation, journal ID and UI details/artwork |
| Different tracks with the same title stay distinct | NOT TESTED | Only one source used in this run |
| Repeated URL reuses file without duplicate Music track | PASS | Repeat exit 0; cached-file message; one UI row afterward |
| Batch with repeated URL avoids duplicate track | PASS | Two-URL batch exit 0; one UI row afterward |
| Playlist with commas, quotes and Unicode | NOT TESTED | Playlist disabled for this run |
| Missing ffmpeg / ffprobe | NOT TESTED | Tools were present |
| Missing Music Automation permission | NOT TESTED | Existing permission allowed actual import |
| Interrupted network transfer and retry | NOT TESTED | No observed network interruption |
| Representative long track | NOT TESTED | The 32-second demo source does not establish long-track behavior |
| Cloud Matched/Uploaded and iPhone appearance | NOT TESTED | New cloud library creation pending; no measured cloud wait |
| iPhone download and playback with Wi-Fi/cellular off | NOT TESTED | No phone playback observation or footage yet |
| Finder transfer and offline playback | N/A | Approved route is cloud; no Finder transfer claim |
| Real CarPlay and offline playback | NOT TESTED | Owner footage and vehicle details still needed |

## Next observations and release decision

1. Create the new initially empty Mac test library via Music's Option-launch
   chooser. Verify its library/media paths before importing only the demo source.
2. Run the authorized cloud route; record upload start, actual Matched/Uploaded
   state and first phone appearance. Keep cloud wait separate from local import.
3. Record the iPhone finding/downloading the track, then restarting playback
   with Wi-Fi and cellular data disabled. Record failures accurately.
4. In a parked vehicle, record the actual CarPlay track selection, advancing
   elapsed time and audible playback; test offline without adding a soundtrack
   over the evidence. Retain raw footage for caption editing.
5. Resolve the remaining required release scenarios with separate real evidence.
   The short demo and its local passes do not cover every release criterion.

**Overall gate: NOT TESTED.** No iPhone/CarPlay row passes solely because the
owner has those devices or enabled sync. The owner agreed to eventually combine
the planned patch/minor changes into v2.1.0 and document skipping v2.0.2; this
record does not authorize publication before acceptance, review and merge.
Issue #88's three demo acceptance criteria remain open. Roadmap #94 is unchanged.
