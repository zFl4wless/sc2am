# macOS entry point and audio-format decisions

This record completes the evaluations in [#90](https://github.com/zFl4wless/sc2am/issues/90)
and [#91](https://github.com/zFl4wless/sc2am/issues/91). Both decisions are to retain
the current CLI and MP3 workflow and defer additional supported features. An
evaluation can be complete without implementing its proposed feature.

Baseline: v2.1.0 behavior, main commit `d8ab338`. Local experiments used macOS
27.0, FFmpeg 9.0.2 and yt-dlp 2026.07.04. These are development checks and
synthetic measurements, not usability, listening or device acceptance tests.

## #90: a clipboard entry point

### Concrete workflow problem

The [installation instructions](../README.md#end-user-installation-on-macos) use a virtual
environment. On subsequent runs, a user copies a track link, opens Terminal,
activates that environment and enters `sc2am download URL`. A clipboard shortcut
could remove the repeated Terminal and command-entry steps after installation.
This problem follows from the documented workflow; no user feedback is claimed.

### Prototype and checks

The proposed flow is **Get Clipboard → Run Shell Script (input to stdin) →
Show Result**. The following shell component was tested with supplied stdin.
It deliberately previews only; it does not download or control Music.

Set `SC2AM_BIN` to the absolute executable path in the installed environment.
For a future real-import flow, external tools must also be on PATH; a shortcut
cannot assume the interactive shell's PATH. `SC2AM_TOOL_PATH` can supply those
directories without prescribing a particular installation location.

```sh
#!/bin/sh
# Evaluation only: validate and preview one URL from stdin.
set -eu
: "${SC2AM_BIN:?Set SC2AM_BIN to the absolute path of the installed sc2am executable}"
case "$SC2AM_BIN" in
    /*) ;;
    *) echo 'SC2AM_BIN must be an absolute path.' >&2; exit 2 ;;
esac
if [ ! -x "$SC2AM_BIN" ]; then
    echo 'SC2AM_BIN is not executable; check the installation path.' >&2
    exit 2
fi
url=$(cat)
case "$url" in
    '') echo 'Copy one SoundCloud track URL first.' >&2; exit 2 ;;
    *'
'*) echo 'Supply one URL, not multiple lines.' >&2; exit 2 ;;
esac
PATH="${SC2AM_TOOL_PATH:+$SC2AM_TOOL_PATH:}$(dirname "$SC2AM_BIN"):$PATH"
export PATH
exec "$SC2AM_BIN" download --strict-import --dry-run -- "$url"
```

Checks passed with `/bin/sh`:

- An executable path containing spaces and URLs containing `&`, quotes,
  backticks and command-substitution text reach a stub CLI as literal arguments.
  No injected command executes. `--` prevents a URL from becoming an option.
- Empty input, multiple lines, relative paths and missing executables fail.
- A stub CLI's exit code 1 and diagnostic stderr propagate unchanged.
- The actual checkout CLI, with `PYTHONPATH=.` and an isolated configuration,
  previews a supported track URL with exit code 0. A non-SoundCloud URL and
  `--help` supplied as input fail URL validation with exit code 2. No download
  directory is created.

The Shortcuts actions were not installed or run. GUI presentation of stderr,
Automation prompts and real downloads through this launcher remain unverified.
`--dry-run` validates input; it does not establish source availability, tool
readiness or a successful Music import. A real-import launcher would need to
handle both stdout and stderr, preserve status, and show partial Music failures
using `--strict-import`; simply displaying successful stdout is insufficient.

### Effort, permissions and feedback comparison

| Route | Setup and repeated use | Permissions and errors |
| --- | --- | --- |
| Existing CLI | Install once; activate the environment and paste a command | Existing Music Automation setup; terminal shows stage summaries and diagnostics |
| Clipboard shortcut | Same installation plus executable/tool paths and shortcut actions; copy a URL and invoke a shortcut | Script execution must be allowed; Music authorization must be checked for the new launcher; stdout/stderr need explicit presentation |
| Finder Quick Action | Same dependencies plus input and extension configuration; useful for files or selected content | Adds configuration without solving the browser-link input problem more directly |

Apple documents [Shortcuts script permissions](https://support.apple.com/en-gb/guide/shortcuts-mac/apdfeb05586f/mac)
and [shortcut launch surfaces](https://support.apple.com/guide/shortcuts-mac/launch-a-shortcut-from-another-app-apd163eb9f95/mac).
The existing [Music permission guidance](macos-setup.md#grant-automation-permission)
applies to the app launching SC2AM. A shortcut does not make this Mac CLI runnable
on an iPhone.

### Decision

**Defer a supported shortcut or Quick Action.** The prototype shows that a thin
adapter can reuse the CLI, but it does not simplify first installation or remove
permission and error-handling work. Keep the CLI as the supported entry point.
A future implementation should begin with an executable discovery/setup design
and verify actual Shortcuts diagnostics and Music authorization. Those would be
new implementation work, not unfinished acceptance criteria for this evaluation.

## #91: source formats and MP3 output

### Available sources and the current conversion path

[SoundCloud's upload documentation](https://help.soundcloud.com/hc/en-us/articles/46021990888219)
describes streaming MP3 and Opus, eligible AAC streams, and creator-enabled
original downloads. [HQ streaming](https://help.soundcloud.com/hc/en-us/articles/360051838074-High-Quality-streaming)
requires the applicable subscription and source eligibility. An upload format
does not guarantee that the same original file is accessible to SC2AM.

The installed [yt-dlp SoundCloud extractor](https://github.com/yt-dlp/yt-dlp/blob/2026.07.04/yt_dlp/extractor/soundcloud.py)
handles those streaming formats and attempts an original download when available.
Actual selection depends on the formats returned for the track and access
conditions; no live track or premium account was sampled for this evaluation.

SC2AM requests `bestaudio/best`, extracts audio to MP3 and supplies quality `192`.
The [yt-dlp postprocessor](https://github.com/yt-dlp/yt-dlp/blob/2026.07.04/yt_dlp/postprocessor/ffmpeg.py)
**skips conversion when the input is already MP3**. Therefore the setting is a
conversion target, not a guarantee that every output is 192 kbit/s. An AAC source
does require lossy conversion to the current MP3 target. The local fixture checks
below exercised the same extraction flags.

### Compatibility comparison

| Candidate | Music.app evidence | SC2AM integration impact |
| --- | --- | --- |
| MP3 | Established application format and existing import validation | Current supported contract; already-MP3 sources need no new encoding |
| AAC in M4A | Apple documents AAC conversion and adding M4A exports to Music | Could avoid another lossy encode for an available AAC source; needs M4A metadata, identity marker, cache and import changes |
| ALAC in M4A | Apple's M4A export guide includes Apple Lossless and adding the file to Music | Useful for an accessible lossless source; cannot restore information missing from a lossy source; same integration changes |
| WAV / AIFF | Apple's Music conversion guide includes these uncompressed formats | Much larger for decoded lossy input; requires a different tagging/identity strategy |
| Opus / FLAC | Native Music import was not established by the Apple sources checked here or by a live test | Keep converting to a supported target; do not promise direct import |

Sources: [Music format conversion](https://support.apple.com/guide/music/convert-music-file-formats-musfb0cea9fa/mac)
and [M4A export to Music](https://support.apple.com/guide/logicpro/m4a-aac-bounce-options-lgcp9e3dfedf/mac).
Documentation of Music format support is distinct from SC2AM support. No new
format was imported into a real Music library or tested on iPhone/CarPlay here.

The current application verifies `.mp3` in `Downloader`, `History`,
`MetadataWriter` and `AppleMusicManager`. Tags, artwork and the recovery marker
use ID3. A format switch in yt-dlp alone would fail those downstream contracts.

### Measured file size and sample preservation

The [reproduction utility](experiments/audio_formats.py) generates a deterministic
30-second, stereo, 44.1-kHz, 16-bit test signal with tones, sweeps, modulation and
seeded noise. It creates illustrative MP3/AAC sources, runs local yt-dlp
extraction fixtures, and compares decoded stereo signed-16-bit PCM SHA-256 values.
It never accesses SoundCloud or Music. [Recorded results](experiments/audio-format-results-2026-10-09.json)
contain byte counts and full hashes. Container metadata can affect size.

| Fixture / operation | Bytes | Decoded PCM comparison |
| --- | ---: | --- |
| Synthetic reference WAV | 5,292,044 | Reference |
| MP3 source at 128 kbit/s | 481,114 | Lossy source |
| Same MP3 through current yt-dlp extraction | 481,114 | Identical to MP3 source |
| AAC source with 256-kbit/s target | 923,525 | Lossy source; measured size is encoder-dependent |
| AAC stream copy to M4A | 923,525 | Identical to AAC source |
| AAC through current MP3/192 extraction | 721,748 | Different from AAC source |
| AAC decoded to 16-bit WAV | 5,292,078 | Identical to AAC source's 16-bit decoded PCM |
| That WAV encoded as ALAC | 4,333,904 | Identical to the decoded WAV |
| Reference encoded as Opus/64 | 341,887 | Different from reference |
| Reference encoded as FLAC | 3,085,696 | Identical to reference |

The AAC→ALAC path intentionally uses the same 16-bit decoded WAV as its reference;
it does not claim preservation of all floating-point decoder output. The larger
WAV/ALAC files contain the already-decoded lossy signal, not recovered original
detail. [Apple explains compression's limits](https://support.apple.com/en-us/108961).
[FFmpeg stream copy](https://ffmpeg.org/ffmpeg.html#Streamcopy) avoids decoding and
re-encoding when the selected codec/container combination permits it.

These measurements establish sizes and sample equality for these fixtures only.
A differing hash does not establish an audible difference, and identical 16-bit
PCM does not establish listening preference. No blind listening test, bitrate
equivalence between codecs or universal quality ranking is claimed.

To reproduce with the required tools on PATH, choose a directory that does not
yet exist:

```sh
python3 docs/experiments/audio_formats.py /tmp/sc2am-audio-comparison
```

FFmpeg needs `libmp3lame` and `libopus`. Other encoder/tool versions may change
byte counts and hashes. The utility fails if the output directory already exists.

### Decision

**Keep MP3 as the default and defer configurable/source-preserving output.**
Preserving an available AAC stream has a concrete technical advantage: avoiding
one additional lossy encode. That alone does not establish a tested compatible
SC2AM option. Adding it requires format-aware metadata, artwork, history hashes,
source markers and import/recovery tests before a release. Lossless conversion
of an already-lossy stream is not a quality upgrade.

A future narrow proposal could preserve AAC in M4A when available, retain MP3
fallback, and prove tags, duplicate prevention, interrupted-import recovery and
device compatibility. There is no supported format flag or promised release in
this evaluation. Both exploration issues can close with these recorded decisions.
