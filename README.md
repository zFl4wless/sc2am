# SC2AM - SoundCloud to Apple Music Automation Tool

A Python CLI tool that automates downloading tracks from SoundCloud and importing them into Apple Music on macOS.

The downloaded MP3 files are automatically enriched with SoundCloud metadata (title, artist, album, genre, date) and cover artwork, so Apple Music shows the correct track information after import.

## Installation

### Requirements
- **macOS** (Apple Music integration requires macOS)
- **Python 3.8+**
- **yt-dlp** (will be installed as dependency)

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

**Download and add to playlist:**
```bash
python main.py download "https://soundcloud.com/artist/track" --playlist "My Playlist"
```

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
python main.py download "https://soundcloud.com/artist/track"
```

**Configuration Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `download_dir` | Path | `~/Downloads/sc2am` | Where to download MP3 files |
| `music_library_path` | Path | auto-detect | Path to Music.app library |
| `default_playlist` | String | none | Default playlist for imports |
| `keep_downloads` | Bool | `true` | Keep MP3 files after import |
| `open_music_app` | Bool | `true` | Auto-open Music.app |
| `log_level` | String | `INFO` | Logging level |
| `log_file` | Path | none | Optional log file path |

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

## Troubleshooting

### yt-dlp not found
```bash
pip install yt-dlp --upgrade
```

### Apple Music not opening
- Ensure Music.app is installed (comes with macOS)
- Check your `open_music_app` setting in config

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
