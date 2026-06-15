"""
SC2AM - SoundCloud to Apple Music automation tool
Command-line interface and main entry point
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, NoReturn, cast

import click

from sc2am.config_manager import ConfigManager, LOG_LEVELS
from sc2am.logger import setup_logging
from sc2am.validator import URLValidator
from sc2am.downloader import Downloader
from sc2am.apple_music import AppleMusicManager


def _exit_with_error(logger, message: str, detail: Optional[str] = None) -> NoReturn:
    logger.error(detail or message)
    raise click.ClickException(message)


def _create_downloader(cfg, logger) -> Downloader:
    try:
        return Downloader(cfg.download_dir)
    except RuntimeError as exc:
        _exit_with_error(logger, "Unable to prepare downloads.", str(exc))


def _require_downloaded_file(file_path: Optional[Path], logger) -> Path:
    if file_path is None:
        _exit_with_error(
            logger,
            "Download finished, but the MP3 file could not be located.",
        )
    return file_path


def _context_state(ctx: Any) -> Dict[str, Any]:
    return cast(Dict[str, Any], ctx.obj)


def _track_label(index: Optional[int] = None, total: Optional[int] = None) -> str:
    if index is not None and total is not None:
        return f"Track {index}/{total}"
    return "Track"


def _track_status(
    logger,
    label: str,
    message: str,
    fg: str = 'blue',
    bold: bool = False,
    level: str = 'info',
) -> None:
    click.secho(f"{label}: {message}", fg=fg, bold=bold)
    logger.log(getattr(logging, level.upper(), logging.INFO), f"{label}: {message}")


def _resolve_playlist_name(cfg, playlist: Optional[str]) -> Optional[str]:
    candidate = (playlist or "").strip()
    if candidate:
        return candidate

    default_playlist = getattr(cfg, "default_playlist", None)
    if default_playlist:
        return str(default_playlist).strip() or None

    return None


def _print_run_summary(logger, succeeded: int, failed: int) -> None:
    summary = f"Summary: {succeeded} succeeded, {failed} failed"
    fg = 'green' if failed == 0 else 'yellow'
    click.secho(summary, fg=fg, bold=True)
    logger.info(summary)


@click.group()
@click.option(
    '--config',
    type=click.Path(exists=True),
    help='Path to custom config file'
)
@click.option(
    '--log-level',
    type=click.Choice(LOG_LEVELS),
    default=ConfigManager.default_config_data()["log_level"],
    help='Logging level'
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], log_level: str):
    """
    SC2AM - Automate downloading SoundCloud tracks and importing them to Apple Music.

    \b
    Examples:
      # Download and open a single track
      sc2am download "https://soundcloud.com/artist/track"

      # Download and add to playlist
      sc2am download "https://soundcloud.com/artist/track" --playlist "My Playlist"

      # Batch process multiple URLs from file
      sc2am batch urls.txt

      # Initialize default config
      sc2am config init
    """
    # Load configuration
    config_path = Path(config) if config else None
    try:
        cfg = ConfigManager.get_config(config_path)
    except Exception as exc:
        raise click.ClickException(
            "Failed to load configuration. Please check your config file and environment variables."
        ) from exc

    # Override log level if specified
    if log_level:
        cfg.log_level = log_level

    # Set up logging
    logger = setup_logging(cfg.log_level, cfg.log_file)

    # Store config in context for subcommands
    state = _context_state(ctx)
    state['config'] = cfg
    state['logger'] = logger


@cli.command()
@click.argument('url')
@click.option(
    '--playlist',
    help='Add to this playlist (optional)'
)
@click.option(
    '--no-open',
    is_flag=True,
    help='Don\'t automatically open with Apple Music'
)
@click.pass_context
def download(ctx: click.Context, url: str, playlist: Optional[str], no_open: bool):
    """
    Download a track from SoundCloud and import to Apple Music.

    URL should be a valid SoundCloud track URL.
    """
    state = _context_state(ctx)
    cfg = state['config']
    logger = state['logger']
    track_label = _track_label()
    succeeded = 0
    failed = 0

    try:
        logger.info(f"Processing URL: {url}")

        # Validate URL
        _track_status(logger, track_label, "Validating SoundCloud URL...")
        is_valid, platform = URLValidator.validate_url(url)
        if not is_valid:
            failed = 1
            _exit_with_error(logger, platform)

        _track_status(logger, track_label, f"OK: Valid {platform} URL", fg='green')
        logger.debug(f"URL validated as {platform}")

        # Download track
        _track_status(logger, track_label, "Downloading track...")
        downloader = _create_downloader(cfg, logger)
        success, file_path, message = downloader.download(url)

        if not success:
            failed = 1
            _exit_with_error(logger, message)

        file_path = _require_downloaded_file(file_path, logger)

        _track_status(logger, track_label, f"OK: {message}", fg='green')
        logger.info(f"Successfully downloaded to {file_path}")

        # Open with Apple Music
        if not no_open and cfg.open_music_app:
            _track_status(logger, track_label, "Opening with Apple Music...")
            music_manager = AppleMusicManager()
            success, msg = music_manager.open_file_with_music(file_path)
            if success:
                _track_status(logger, track_label, f"OK: {msg}", fg='green')
                logger.info(msg)
            else:
                _track_status(logger, track_label, f"WARNING: {msg}", fg='yellow')
                logger.warning(msg)

        playlist_name = _resolve_playlist_name(cfg, playlist)

        # Add to playlist
        if playlist_name:
            _track_status(logger, track_label, f"Adding to playlist '{playlist_name}'...")
            music_manager = AppleMusicManager()
            success, msg = music_manager.add_to_playlist(file_path, playlist_name)
            if success:
                _track_status(logger, track_label, f"OK: {msg}", fg='green')
                logger.info(msg)
            else:
                _track_status(logger, track_label, f"WARNING: {msg}", fg='yellow')
                logger.warning(msg)

        succeeded = 1
        click.secho(f"\n{track_label}: Done!", fg='green', bold=True)
    finally:
        _print_run_summary(logger, succeeded, failed)


@cli.command()
@click.argument('batch_file', type=click.Path(exists=True))
@click.option(
    '--playlist',
    help='Add all tracks to this playlist (optional)'
)
@click.option(
    '--continue-on-error',
    is_flag=True,
    help='Continue processing if a URL fails'
)
@click.pass_context
def batch(ctx: click.Context, batch_file: str, playlist: Optional[str], continue_on_error: bool):
    """
    Process multiple URLs from a text file (one URL per line).

    Lines starting with # are treated as comments and ignored.
    """
    state = _context_state(ctx)
    cfg = state['config']
    logger = state['logger']

    logger.info(f"Processing batch file: {batch_file}")

    # Validate batch file
    all_valid, urls, errors = URLValidator.validate_batch_file(batch_file)

    if errors:
        for line_num, error in errors:
            click.secho(f"ERROR: Line {line_num}: {error}", fg='red')
            logger.error(f"Line {line_num}: {error}")

    if not urls:
        _exit_with_error(logger, "No valid URLs found in batch file.")

    click.secho(f"OK: Found {len(urls)} valid URL(s)", fg='green')
    logger.info(f"Found {len(urls)} valid URLs")

    # Process each URL
    downloader = _create_downloader(cfg, logger)

    music_manager = AppleMusicManager()
    successful = 0
    failed = 0
    abort_with_error = False

    try:
        for i, url in enumerate(urls, 1):
            track_label = _track_label(i, len(urls))
            click.echo(f"\n{track_label}: Processing {url}")
            logger.debug(f"Processing URL {i}/{len(urls)}")

            # Download
            _track_status(logger, track_label, "Downloading track...")
            success, file_path, message = downloader.download(url)
            if not success:
                _track_status(logger, track_label, f"ERROR: {message}", fg='red', level='error')
                failed += 1
                if not continue_on_error:
                    abort_with_error = True
                    break
                continue

            file_path = _require_downloaded_file(file_path, logger)

            _track_status(logger, track_label, "OK: Downloaded", fg='green')
            successful += 1

            # Open with Apple Music
            if cfg.open_music_app:
                _track_status(logger, track_label, "Opening with Apple Music...")
                success, msg = music_manager.open_file_with_music(file_path)
                if success:
                    _track_status(logger, track_label, "OK: Opened with Apple Music", fg='green')
                else:
                    _track_status(logger, track_label, f"WARNING: {msg}", fg='yellow', level='warning')

            playlist_name = _resolve_playlist_name(cfg, playlist)

            # Add to playlist
            if playlist_name:
                _track_status(logger, track_label, f"Adding to playlist '{playlist_name}'...")
                success, msg = music_manager.add_to_playlist(file_path, playlist_name)
                if success:
                    _track_status(logger, track_label, "OK: Added to playlist", fg='green')
                else:
                    _track_status(logger, track_label, f"WARNING: {msg}", fg='yellow', level='warning')

            click.secho(f"{track_label}: Done!", fg='green', bold=True)
    finally:
        _print_run_summary(logger, successful, failed)

    if abort_with_error:
        sys.exit(1)


@cli.group()
def config():
    """Manage SC2AM configuration."""
    pass


@config.command('init')
@click.option('--force', is_flag=True, help='Overwrite existing config')
@click.pass_context
def config_init(ctx: click.Context, force: bool):
    """Initialize default configuration file."""
    logger = _context_state(ctx)['logger']

    click.echo("Initializing SC2AM configuration...")
    try:
        config_path = ConfigManager.create_default_config(force=force)
    except Exception as exc:
        _exit_with_error(
            logger,
            "Could not create the configuration file.",
            str(exc),
        )

    click.secho(f"OK: Configuration file created at: {config_path}", fg='green')
    logger.info(f"Config initialized at {config_path}")


@config.command('show')
@click.pass_context
def config_show(ctx: click.Context):
    """Display current configuration."""
    cfg = _context_state(ctx)['config']

    click.echo("\nCurrent Configuration:")
    click.echo("=" * 50)
    click.echo(f"Download Directory:  {cfg.download_dir}")
    click.echo(f"Music Library:       {cfg.music_library_path or '(auto-detect)'}")
    click.echo(f"Default Playlist:    {cfg.default_playlist or '(none)'}")
    click.echo(f"Keep Downloads:      {cfg.keep_downloads}")
    click.echo(f"Open Music App:      {cfg.open_music_app}")
    click.echo(f"Log Level:           {cfg.log_level}")
    click.echo(f"Log File:            {cfg.log_file or '(console only)'}")
    click.echo("=" * 50)


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except Exception:
        logging.getLogger("sc2am").exception("Unhandled CLI error")
        click.secho(
            "ERROR: An unexpected error occurred. Please check the log file for details.",
            fg='red',
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
