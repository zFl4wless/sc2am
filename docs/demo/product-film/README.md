# SC2AM animated product film — revised cut

[Watch the 36-second MP4](sc2am-product-film.mp4) ·
[English subtitles](captions.en.vtt) · [Editable composition](index.html)

A 1920×1080, 30-fps **animated product overview**, made locally with
[Hyperframes](https://github.com/heygen-com/hyperframes) at the owner's request
instead of collecting raw device footage. Seven short headlines serve as the burned-in captions and have a matching VTT.
Each scene pairs one sentence of at most four words with a large visual; the
cover connects the illustrated steps. Small evidence labels remain visible. There is no narration; the original authorized demo
track supplies background music. The composition is reviewable and editable.

## What is real and what is illustrated

- Link/MP3 scenes: an illustrated link entry and tagged-file motif. The actual
  tested command is documented below; no terminal recording is presented.
- Music scene: the actual sanitized Mac Details screenshot from the
  [dated acceptance run](../device-acceptance-2026-10-08.md), cropped only by the
  HTML viewport. Visible title, artist, genre and cover match the tested MP3.
- Cloud scene: a graphic describing an earlier Mac observation, not a live
  upload. Uploaded was first observed 48.539 seconds after enabling sync;
  actual completion may have been earlier, and iPhone arrival time is unknown.
- Phone/car scenes: clearly labeled device illustrations. iPhone download/offline
  playback and real wireless BMW CarPlay were reported by the owner in the
  acceptance run. No device capture, audible device output or advancing fake
  playback counter is presented. The music bed is not playback evidence.
- Timing: seven designed scenes with animated entrances/exits, at 0/5/10/17/22/27/32
  seconds; these are editorial timing, not measured end-to-end execution times.

No Mac library, Apple Account, phone setting or vehicle was accessed to create
this animation. It does not fulfill issue #88's original real-device-footage
criterion. That criterion remains open; the owner chose this illustrated
alternative. The previous [filming plan](../recording-plan.md) is retained for
reference, not as a request to record footage now. No release/tag is created and
roadmap #94 remains unchanged pending review and merge.

## Prerequisites and actual SC2AM command

Follow the [macOS setup guide](../../macos-setup.md): macOS, Python 3.10+,
FFmpeg/ffprobe, Music.app and Music Automation permission. The cloud route
additionally requires an authorized Apple Music or iTunes Match subscription,
the same Apple Account on Mac/iPhone, Sync Library, network access and enough
storage. Download the track on the phone before using it offline; wireless
CarPlay needs Wi-Fi/Bluetooth for the connection. SC2AM confirms only Mac import.

Run from the repository root with the virtual environment first on PATH and
inherited `SC2AM_*` overrides removed. The actual successful command was:

```bash
.venv/bin/python main.py --config "<demo-root>/config.yaml" \
  download "https://soundcloud.com/fl4wless-167171478/midnight-circuit" \
  --open --playlist "" --stop-on-error --strict-import
```

`<demo-root>` substitutes only the generated isolated local directory. Its
config selects downloads, not the Music library; verify the authorized active
library first. The initial real run exited 0 in 4.472 seconds. Later repeats
reused the verified file. Full config, logs, scope, versions and source IDs are
in the dated record; the animation does not conduct a new transfer.

## Rebuild or edit

This video project is isolated from the Python application's dependencies.
Node.js 22+, FFmpeg/ffprobe and a supported Chrome/headless Chrome are required.
The tool can populate browser/font caches on its first run; no HeyGen account or
cloud render is used. The pinned dependency lockfile is included.

```bash
cd docs/demo/product-film
npm ci --ignore-scripts
DO_NOT_TRACK=1 HYPERFRAMES_NO_TELEMETRY=1 npm run check
DO_NOT_TRACK=1 HYPERFRAMES_NO_TELEMETRY=1 npm run preview
DO_NOT_TRACK=1 HYPERFRAMES_NO_TELEMETRY=1 npm run render
```

The actual render used the locally installed Hyperframes 0.8.141 CLI with:

```bash
DO_NOT_TRACK=1 HYPERFRAMES_NO_TELEMETRY=1 \
  node node_modules/hyperframes/dist/cli.js render \
  --output sc2am-product-film.mp4 --fps 30 --workers 2 --crf 22 \
  --strict --no-best-effort
```

Edit `index.html` and keep `captions.en.vtt` aligned with its seven headline captions.
Audio/artwork provenance, credits and third-party notices are in
[NOTICE.md](NOTICE.md). Output validation and hashes are in
[validation.json](validation.json).

## Validation scope

Hyperframes check sampled 2.5/7.5/13.5/19.5/24.5/29.5/34 seconds: no lint
errors, runtime errors, layout warnings/errors or contrast failures (31/31
checks passed). Its eight structural lint warnings are retained: seven
suggestions to split scene sections into sub-compositions and one dense-track
warning. The shared moving cover keeps this short composition in one file.
The Music screenshot intentionally clips the lower Details fields; title,
artist, genre and artwork stay visible. Final MP4 keyframes, the cloud-to-phone
transition and the ending were visually reviewed. No motion-pass success is
claimed: that automated pass was disabled by the tool. The local frame render
and final-file checks are distinct from the real-device acceptance record and
hosted CI.
