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
- **Python 3.8+**
- **yt-dlp** (will be installed as dependency)

### macOS Prerequisites

Apple Music automation relies on macOS permissions and Music.app being available locally. Before using SC2AM, make sure:

- **Music.app is installed** and can be opened manually on this Mac.
- **Music.app has been launched at least once** so the library is initialized.
- **Automation permission is allowed** for the app you run SC2AM from, such as Terminal, iTerm, VS Code, or PyCharm.
- **System Settings > Privacy & Security > Automation** allows that app to control Music.
- **The Music library is accessible** on the current macOS account you are using.

For a step-by-step checklist, see [`docs/macos-setup.md`](docs/macos-setup.md).

### Setup

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

4. **Install from source (optional)**
If you want to work on the project or install it in editable mode:
```bash
pip install -e .
```

4. **Initialize configuration (optional):**
```bash
python main.py config init
```

This creates a default config at `~/.sc2am/config.yaml`.

## Usage

### Quick Start

SoundCloud-Links must point to a single track, for example:
`https://soundcloud.com/artist/track`
or `https://www.soundcloud.com/artist/track`.

**Download a single track:**
```bash
python main.py download "https://soundcloud.com/artist/track"
```

**Download multiple tracks in one run:**
```bash
python main.py download \
  "https://soundcloud.com/artist/track1" \
  "https://soundcloud.com/artist/track2"
```

If you want to keep processing after one URL fails, use:
```bash
python main.py download \
  "https://soundcloud.com/artist/track1" \
  "https://soundcloud.com/artist/track2" \
  --continue-on-error
```

**Download and add to playlist:**
```bash
python main.py download "https://soundcloud.com/artist/track" --playlist "My Playlist"
```

If you do not pass `--playlist`, SC2AM uses the configured `default_playlist` when one is set. Playlist names are matched against the playlists currently available in Apple Music, and the app will tell you clearly if the playlist is missing or if the name is duplicated.

**Don't automatically open Music app:**
```bash
python main.py download "https://soundcloud.com/artist/track" --no-open
```

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
python main.py batch urls.txt
```

**Batch options:**
```bash
# Add all tracks to a playlist
python main.py batch urls.txt --playlist "My Playlist"

# Continue processing even if a URL fails
python main.py batch urls.txt --continue-on-error
```

### Configuration

**View current configuration:**
```bash
python main.py config show
```

**Configuration File** (`~/.sc2am/config.yaml`):
```yaml
download_dir: ~/Downloads/sc2am
music_library_path: null
default_playlist: null
keep_downloads: true
open_music_app: true
normalize_metadata: true
skip_existing_tracks: false
log_level: INFO
log_file: null
```

**Environment Variables:**
Override config file settings with environment variables:
```bash
SC2AM_DOWNLOAD_DIR=~/Music/Downloads
SC2AM_PLAYLIST="My Playlist"
SC2AM_LOG_LEVEL=DEBUG
SC2AM_KEEP_DOWNLOADS=false
SC2AM_NORMALIZE_METADATA=true
SC2AM_SKIP_EXISTING=false
python main.py download "https://soundcloud.com/artist/track"
```

**Configuration Options:**

| Option                | Type   | Default             | Description                                          |
|-----------------------|--------|---------------------|------------------------------------------------------|
| `download_dir`        | Path   | `~/Downloads/sc2am` | Where to download MP3 files                          |
| `music_library_path`  | Path   | auto-detect         | Path to Music.app library                            |
| `default_playlist`    | String | none                | Default playlist for imports (workflow setting)      |
| `keep_downloads`      | Bool   | `true`              | Keep MP3 files after import                          |
| `open_music_app`      | Bool   | `true`              | Auto-open Music.app                                  |
| `normalize_metadata`  | Bool   | `true`              | Normalize and tag track metadata (workflow setting)  |
| `skip_existing_tracks`| Bool   | `false`             | Skip tracks already in Music library (workflow)      |
| `log_level`           | String | `INFO`              | Logging level (workflow setting)                     |
| `log_file`            | Path   | none                | Optional log file path                               |

### Global Options

```bash
# Use custom config file
python main.py --config /path/to/config.yaml download "..."

# Set log level
python main.py --log-level DEBUG download "..."
```

### Advanced Examples

**Batch download with logging:**
```bash
python main.py --log-level DEBUG batch urls.txt --continue-on-error
```

**Download to custom directory:**
```bash
SC2AM_DOWNLOAD_DIR=~/Music python main.py download "..."
```

## How It Works

1. **Validate** - Checks if the provided URL is from a supported platform
2. **Download** - Uses yt-dlp to download audio as MP3 (192kbps)
3. **Tag** - Embeds title, artist, album/genre/date and cover artwork into the MP3
4. **Open** - Launches Apple Music with the tagged MP3 file
5. **Add** - (Optional) Adds track to specified playlist via AppleScript

SC2AM automatically retries transient download and Apple Music import failures a few times before surfacing an error, so brief network hiccups or a busy Music.app are less likely to interrupt a run.

### Exit Codes and Logging Behavior

SC2AM now returns stable exit codes for scripting:

- `0` - all requested work succeeded
- `1` - at least one item failed during processing
- `2` - usage/input error (for example invalid CLI input or invalid configuration)

CLI progress output is written as clean status lines. Python logger output on the console is limited to warnings and errors so informational log lines do not duplicate the CLI status messages. To retain detailed logs, configure `log_file`.

### Batch Processing Output

When running batch operations with multiple links or URLs from a file, SC2AM provides improved logging and summary output to help you debug and understand the results:

- **Grouped logs** - Each track is clearly separated with visual dividers for easy scanning
- **Real-time status** - Per-track status updates show what SC2AM is doing (downloading, opening, adding to playlist)
- **Success rate** - Final summary includes percentage of successful imports
- **Failed track details** - If any tracks fail, the summary lists each failed URL with its specific error message

Example output:
```
──────────────────────────────────────────────
Track 1/3: Processing https://soundcloud.com/artist/track1
Track 1/3: Validating SoundCloud URL...
Track 1/3: OK: Valid SoundCloud URL
Track 1/3: Downloading track...
Track 1/3: OK: Downloaded: track1.mp3
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
Track 3/3: OK: Downloaded: track3.mp3
Track 3/3: Done!

Summary: 2 succeeded, 1 failed (67% success rate)

Failed tracks:
  1. https://soundcloud.com/artist/track2
     Error: Track not found
```

## Troubleshooting

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
- Playlist name must exactly match your Music.app playlists
- Ensure the Music.app is not currently playing (can interfere with AppleScript)

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
black sc2am/

# Linting
flake8 sc2am/
```

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

For issues, feature requests, or questions:
- Open an issue on GitHub
- Check existing issues first
