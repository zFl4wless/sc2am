# SC2AM - SoundCloud to Apple Music Automation Tool

A Python CLI tool that automates downloading tracks from SoundCloud and importing them into Apple Music on macOS.

Overview
--------

SC2AM provides a small, repeatable workflow for importing SoundCloud tracks into your macOS Music library:

- Validate a SoundCloud track URL
- Download the audio using yt-dlp and convert/normalize to MP3
- Embed metadata (title, artist, album, genre, date) and cover artwork
- Open Music.app and import the tagged MP3
- Optionally add the track to a specified playlist

The downloaded MP3 files are automatically enriched with SoundCloud metadata (title, artist, album, genre, date) and cover artwork, with improved title and artist mapping so Apple Music shows the correct track information after import.

## Installation

### Requirements
- **macOS** (Apple Music integration requires macOS)
- **Python 3.10+**
- **yt-dlp** (will be installed as dependency)
- **FFmpeg and ffprobe** (required by yt-dlp to extract and convert MP3 audio)

### macOS Prerequisites

Apple Music automation relies on macOS permissions and Music.app being available locally. Before using SC2AM, make sure:

- **Music.app is installed** and can be opened manually on this Mac.
- **Music.app has been launched at least once** so the library is initialized.
- **Automation permission is allowed** for the app you run SC2AM from, such as Terminal, iTerm, VS Code, or PyCharm.
- **System Settings > Privacy & Security > Automation** allows that app to control Music.
- **The Music library is accessible** on the current macOS account you are using.

For a step-by-step checklist, see [`docs/macos-setup.md`](docs/macos-setup.md).
Release preparation is documented in [`docs/releasing.md`](docs/releasing.md),
and user-facing changes are tracked in [`CHANGELOG.md`](CHANGELOG.md).

### Setup

Install FFmpeg and ffprobe before downloading tracks. On macOS, install both with
Homebrew:

```bash
brew install ffmpeg
```

SC2AM checks for `yt-dlp`, `ffmpeg`, and `ffprobe` when a real download starts.
Help and `--dry-run` do not require these download tools.

1. **Clone or download the project:**
```bash
git clone https://github.com/zfl4wless/sc2am.git
cd sc2am
```

2. **Create a virtual environment (recommended):**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install from source (recommended for the `sc2am` command):**
If you want to work on the project or install it in editable mode:
```bash
pip install -e .
```

5. **Initialize configuration (optional):**
```bash
sc2am config init
```

This creates a default config at `~/.sc2am/config.yaml`.

## Usage

### Quick Start

SoundCloud-Links must point to a single track, for example:
`https://soundcloud.com/artist/track`
or `https://www.soundcloud.com/artist/track`.
Profiles, profile tabs (such as `/likes` or `/tracks`), albums, and sets are
rejected. SC2AM also checks the extracted result before downloading audio;
if it is a collection or cannot be verified as a single track, the download stops.

**Download a single track:**
```bash
sc2am download "https://soundcloud.com/artist/track"
```

**Download multiple tracks in one run:**
```bash
sc2am download \
  "https://soundcloud.com/artist/track1" \
  "https://soundcloud.com/artist/track2"
```

If you want to keep processing after one URL fails, use:
```bash
sc2am download \
  "https://soundcloud.com/artist/track1" \
  "https://soundcloud.com/artist/track2" \
  --continue-on-error
```

**Download and add to playlist:**
```bash
sc2am download "https://soundcloud.com/artist/track" --playlist "My Playlist"
```

If you do not pass `--playlist`, SC2AM uses the configured `default_playlist` when one is set. Playlist names are matched against the playlists currently available in Apple Music, and the app will tell you clearly if the playlist is missing or if the name is duplicated.

Names containing commas, quotes or Unicode characters are supported, for example
`--playlist "Road, Trip"`. Matching ignores case and surrounding whitespace;
the original name is preserved for the import. Choose a regular user playlist:
Smart, Genius, folder and system playlists cannot receive tracks. Duplicate
names must be renamed before importing, even when they occur in different folders.

**Don't automatically open Music app:**
```bash
sc2am download "https://soundcloud.com/artist/track" --no-open
```

For a preview that validates the input and shows the planned actions without
downloading files or accessing Music.app, add `--dry-run`. Use
`--no-open --playlist ""` when you want to disable both Music actions.

### Batch Processing

Create a file `urls.txt` with one URL per line:
```
https://soundcloud.com/artist/track1
https://soundcloud.com/artist/track2
# This is a comment
https://soundcloud.com/artist/track3
```

Then process all URLs:
```bash
sc2am batch urls.txt
```

**Batch options:**
```bash
# Add all tracks to a playlist
sc2am batch urls.txt --playlist "My Playlist"

# Continue processing even if a URL fails
sc2am batch urls.txt --continue-on-error
```

### Configuration

See the [CLI and configuration contract](docs/cli-and-config-contract.md) for the
complete interface. Precedence is explicit CLI options > environment > selected
YAML file > defaults. A custom YAML file replaces the default file. Invalid YAML,
unknown keys, and invalid values are reported instead of silently ignored.

SC2AM ignores external yt-dlp configuration files for both track information and
audio downloads (`--ignore-config`). Personal yt-dlp settings such as
`--skip-download`, download archives, and match filters do not affect SC2AM.
The SC2AM configuration precedence above remains unchanged.

**View current configuration:**
```bash
sc2am config show
```

**Configuration File** (`~/.sc2am/config.yaml`):
```yaml
download_dir: ~/Downloads/sc2am
default_playlist: null
open_music_app: true
continue_on_error: false
log_level: INFO
log_file: null
```

**Environment variables:**
Use exported variables or prefix the command with assignments. `.env` files are not
loaded automatically.

```bash
SC2AM_DOWNLOAD_DIR=~/Music/Downloads SC2AM_PLAYLIST="My Playlist" SC2AM_LOG_LEVEL=DEBUG \
  sc2am download "https://soundcloud.com/artist/track"
```

**Active settings:**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `download_dir` | Path | `~/Downloads/sc2am` | MP3 destination |
| `default_playlist` | String or null | `null` | Default playlist |
| `open_music_app` | Bool | `true` | Automatically opens MP3s in Music |
| `continue_on_error` | Bool | `false` | Continues after an input/download failure |
| `log_level` | String | `INFO` | DEBUG, INFO, WARNING, ERROR, or CRITICAL |
| `log_file` | Path or null | `null` | Optional detailed log file |

Both `download` and `batch` support `--no-open` / `--open`,
`--continue-on-error` / `--stop-on-error`, `--playlist NAME`, and `--dry-run`.
Omitted options inherit configuration. `--playlist ""` disables the configured
playlist. `--no-open` leaves playlist actions enabled; use both to avoid Music
interaction. Dry runs validate and preview without downloads, file writes, or
Music actions.

### Global Options

```bash
# Use custom config file
sc2am --config /path/to/config.yaml download "..."

# Set log level
sc2am --log-level DEBUG download "..."
```

### Advanced Examples

**Batch download with logging:**
```bash
sc2am --log-level DEBUG batch urls.txt --continue-on-error
```

**Download to custom directory:**
```bash
SC2AM_DOWNLOAD_DIR=~/Music sc2am download "..."
```

## How It Works

1. **Validate** - Checks if the provided URL is from a supported platform
2. **Download** - Uses yt-dlp to download audio as MP3 (192kbps)
3. **Tag** - Embeds title, artist, album/genre/date and cover artwork into the MP3
4. **Open** - Launches Apple Music with the tagged MP3 file
5. **Add** - (Optional) Adds track to specified playlist via AppleScript

SC2AM automatically retries transient download and Apple Music import failures a few times before surfacing an error, so brief network hiccups or a busy Music.app are less likely to interrupt a run.

MP3 filenames include the SoundCloud track ID: `Title [123456789].mp3`.
Tracks with the same title and different IDs are saved separately. Repeating a
download with the same ID and title reuses the existing audio without overwriting
it; metadata is refreshed and the configured Music actions still run. A changed
title produces a new filename. Older title-only files are left untouched and are
not reused by the new naming scheme.

SC2AM only tags and imports the verified MP3 path reported by that download.
Missing or invalid output paths cause a download error, even when other MP3s
already exist in the directory.

### Exit Codes and Logging Behavior

SC2AM now returns stable exit codes for scripting:

- `0` - command completed without input/download failures
- `1` - runtime/download failure or a run that continued past invalid entries
- `2` - usage/configuration error or an input-validation abort

Music open/playlist failures remain warnings and do not change exit status.
Summary success counts describe downloads or dry-run previews, not confirmed imports.

CLI progress output is written as clean status lines. By default, Python logger output on stderr is limited to warnings and errors so informational log lines do not duplicate the CLI status messages. Explicit `--log-level DEBUG` (or `log_level: DEBUG` / `SC2AM_LOG_LEVEL=DEBUG`) includes diagnostic and informational logs on stderr. To retain logs in a file, configure `log_file` or `SC2AM_LOG_FILE`.

### Batch Processing Output

When running batch operations with multiple links or URLs from a file, SC2AM provides improved logging and summary output to help you debug and understand the results:

- **Grouped logs** - Each track is clearly separated with visual dividers for easy scanning
- **Real-time status** - Per-track status updates show what SC2AM is doing (downloading, opening, adding to playlist)
- **Success rate** - Final summary includes percentage of successful downloads or previews
- **Failed track details** - If any tracks fail, the summary lists each failed URL with its specific error message

Example output:
```
──────────────────────────────────────────────
Track 1/3: Processing https://soundcloud.com/artist/track1
Track 1/3: Validating SoundCloud URL...
Track 1/3: OK: Valid SoundCloud URL
Track 1/3: Downloading track...
Track 1/3: OK: Downloaded: track1 [123456789].mp3
Track 1/3: Done!

──────────────────────────────────────────────
Track 2/3: Processing https://soundcloud.com/artist/track2
Track 2/3: Validating SoundCloud URL...
Track 2/3: OK: Valid SoundCloud URL
Track 2/3: Downloading track...
Track 2/3: ERROR: Track not found

──────────────────────────────────────────────
Track 3/3: Processing https://soundcloud.com/artist/track3
Track 3/3: Validating SoundCloud URL...
Track 3/3: OK: Valid SoundCloud URL
Track 3/3: Downloading track...
Track 3/3: OK: Downloaded: track3 [987654321].mp3
Track 3/3: Done!

Summary: 2 succeeded, 1 failed (67% success rate)

Failed tracks:
  1. https://soundcloud.com/artist/track2
     Error: Track not found
```

## Troubleshooting

### Diagnose an unexpected failure

No log file is created by default (`log_file: null`). Generic errors show how to
enable diagnostics; dependency, path, URL and Music permission errors include
remedies. To see debug output on stderr, replace the example link with the failing
track URL and keep the options from the original command:

```bash
sc2am --log-level DEBUG download "https://soundcloud.com/artist/track"
sc2am --log-level DEBUG batch urls.txt --continue-on-error
```

To save command details, underlying yt-dlp errors and exception tracebacks in a
diagnostic log, set a writable log path:

```bash
SC2AM_LOG_FILE="$PWD/sc2am-debug.log" sc2am --log-level DEBUG download "https://soundcloud.com/artist/track"
SC2AM_LOG_FILE="$PWD/sc2am-debug.log" sc2am --log-level DEBUG batch urls.txt --continue-on-error
```

Put global options before `download` or `batch`. If using a custom configuration,
keep `--config PATH` before the subcommand as well. When running from the source
checkout, replace `sc2am` with `python main.py`. A configured log file retains
underlying errors and exception tracebacks at the default INFO level too; DEBUG
adds command and progress context. These commands repeat the workflow, so check
the Music library and target playlist before retrying a failed or uncertain
import. Review logs for private URLs and local paths before sharing them.

`--dry-run` validates and previews only: it suppresses log-file writes and does
not reproduce download or Music failures. `config show` also does not write a
log file.

### yt-dlp not found
```bash
pip install yt-dlp --upgrade
```

### Apple Music not opening
- Ensure Music.app is installed (comes with macOS)
- Check your `open_music_app` setting in config
- Confirm the app you use to run SC2AM has Automation permission for Music in System Settings

### macOS permissions or prerequisites are missing
- Open Music.app once manually and confirm it launches without errors
- Go to **System Settings > Privacy & Security > Automation** and allow the app you use to run SC2AM to control Music
- If you previously denied access, re-run SC2AM after re-enabling the permission so macOS can prompt again if needed
- See [`docs/macos-setup.md`](docs/macos-setup.md) for the full checklist

### Adding to playlists fails
- Check the playlist name (matching ignores case and surrounding whitespace)
- Rename duplicate playlists and choose a regular user playlist rather than a Smart, Genius, folder or system playlist
- Ensure the Music.app is not currently playing (can interfere with AppleScript)

### Apple Music commands time out
- Each `open` or `osascript` attempt is limited to 30 seconds. Playlist lookups retry temporary failures and timeouts up to three attempts, with 1- and 2-second delays (at most about 93 seconds).
- Open Music.app and check for permission prompts or an unresponsive app.
- Failed file-opening and playlist-import commands are not automatically retried: Music may have received the import before the error or timeout. Check the Music library and target playlist before repeating the import to avoid duplicates. Stopping the command does not undo an import already received by Music.
- Music failures remain CLI warnings; the downloaded MP3 is retained. Successful `open` dispatch still does not confirm a library import, and SC2AM does not yet reconcile uncertain imports or prevent duplicates across separate runs.

### Permission denied on download
- Check that download directory exists and is writable:
```bash
mkdir -p ~/Downloads/sc2am
chmod 755 ~/Downloads/sc2am
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Submit a pull request

### Development Setup

```bash
# Install with dev dependencies
pip install -r requirements-dev.txt

# Code formatting
black --check .

# Linting
flake8 main.py sc2am tests scripts

# Tests
PYTHONPATH=. pytest -q
```

CI runs these checks for pull requests, `main`, and `v*` release tags. It also
builds sdist/wheel artifacts and checks the installed CLI in fresh environments
on Ubuntu and macOS, without a personal Apple account. See
[release validation](docs/releasing.md#automated-checks) for scope and limitations.

Dependency source of truth:
- `pyproject.toml` is the canonical dependency definition.
- `requirements.txt` and `requirements-dev.txt` are thin compatibility wrappers that install from project metadata.

## License

MIT License - see LICENSE file for details

## Disclaimer

- This tool is for personal use to manage legally acquired music
- Respect copyright laws in your jurisdiction
- SoundCloud's terms of service should be respected

## Support

The current stable release line is 2.x. Older release lines are unsupported;
upgrade to the latest 2.x release before requesting help.

For general issues, feature requests, or questions:
- Check existing issues first, then open an issue on GitHub

For suspected security vulnerabilities, do not open a public issue. Report them
privately through [GitHub Security Advisories](SECURITY.md#reporting-a-vulnerability).
