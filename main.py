"""
SC2AM - SoundCloud to Apple Music automation tool
Command-line interface and main entry point
"""

import logging
import sys
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, Optional, NoReturn, Tuple, cast

import click

from sc2am.config_manager import ConfigManager, ConfigurationError, LOG_LEVELS
from sc2am.logger import setup_logging
from sc2am.validator import URLValidator
from sc2am.downloader import Downloader
from sc2am.apple_music import AppleMusicManager


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    USAGE = 2


def _exit_with_error(
    logger,
    message: str,
    detail: Optional[str] = None,
    exit_code: int = int(ExitCode.ERROR),
) -> NoReturn:
    logger.error(detail or message)
    exc = click.ClickException(message)
    exc.exit_code = exit_code
    raise exc


def _create_downloader(cfg, logger) -> Downloader:
    try:
        return Downloader(cfg.download_dir)
    except RuntimeError as exc:
        _exit_with_error(logger, "Unable to prepare downloads.", str(exc))


def _context_state(
    ctx: Any, log_to_file: bool = True, overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    state = cast(Dict[str, Any], ctx.obj)
    if "config" not in state:
        try:
            state["config"] = ConfigManager.get_config(
                state.get("config_path"),
                overrides={**state.get("overrides", {}), **(overrides or {})},
            )
        except ConfigurationError as exc:
            error = click.ClickException(str(exc))
            error.exit_code = int(ExitCode.USAGE)
            raise error from exc
        cfg = state["config"]
        try:
            state["logger"] = setup_logging(cfg.log_level, cfg.log_file if log_to_file else None)
        except OSError as exc:
            raise click.ClickException(
                f"Could not open log file: {cfg.log_file}. Check the path and permissions."
            ) from exc
    return state


def _track_label(index: Optional[int] = None, total: Optional[int] = None) -> str:
    if index is not None and total is not None:
        return f"Track {index}/{total}"
    return "Track"


def _track_status(
    logger,
    label: str,
    message: str,
    fg: str = "blue",
    bold: bool = False,
    level: str = "info",
) -> None:
    click.secho(f"{label}: {message}", fg=fg, bold=bold)
    logger.log(getattr(logging, level.upper(), logging.INFO), f"{label}: {message}")


def _resolve_playlist_name(cfg, playlist: Optional[str]) -> Optional[str]:
    if playlist is not None:
        return playlist.strip() or None

    default_playlist = getattr(cfg, "default_playlist", None)
    if default_playlist:
        return str(default_playlist).strip() or None

    return None


def _print_run_summary(
    logger, succeeded: int, failed: int, failed_items: Optional[list] = None
) -> None:
    total = succeeded + failed
    success_rate = int((succeeded / total * 100)) if total > 0 else 0
    summary = f"Summary: {succeeded} succeeded, {failed} failed ({success_rate}% success rate)"
    fg = "green" if failed == 0 else "yellow"
    click.secho(summary, fg=fg, bold=True)
    logger.info(summary)

    # Print detailed error list if there were failures
    if failed_items and len(failed_items) > 0:
        click.secho("\nFailed tracks:", fg="red", bold=True)
        for idx, (url, error) in enumerate(failed_items, 1):
            click.secho(f"  {idx}. {url}", fg="red")
            click.secho(f"     Error: {error}", fg="red")
            logger.error(f"Failed: {url} - {error}")
        click.echo()


@click.group()
@click.option(
    "--config",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to custom YAML config file (overrides default ~/.sc2am/config.yaml)",
)
@click.option(
    "--log-level",
    type=click.Choice(LOG_LEVELS, case_sensitive=False),
    default=None,
    help="Logging level (overrides environment and config file)",
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], log_level: Optional[str]):
    """SC2AM - Automate downloading SoundCloud tracks and importing them to Apple Music.

    Use `sc2am --help` and `sc2am <command> --help` for command-specific options.

    \b
    Examples:
      sc2am download "https://soundcloud.com/artist/track"
      sc2am download URL --playlist "My Playlist"
      sc2am batch urls.txt --continue-on-error
      sc2am config init
    """
    # Load only when a command needs configuration, so help and init can recover
    # from an invalid file or environment without triggering logging side effects.
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["overrides"] = {"log_level": log_level} if log_level is not None else {}


def _run_tracks(
    cfg,
    logger,
    urls: Tuple[str, ...],
    playlist: Optional[str],
    no_open: Optional[bool],
    continue_on_error: Optional[bool],
    dry_run: bool,
    input_errors: Optional[list] = None,
    numbered: bool = False,
) -> None:
    """Apply one workflow to single URLs, multiple URLs, and batch files."""
    effective_continue = (
        getattr(cfg, "continue_on_error", False) if continue_on_error is None else continue_on_error
    )
    open_music = cfg.open_music_app if no_open is None else not no_open
    playlist_name = _resolve_playlist_name(cfg, playlist)
    failed_items = list(input_errors or [])
    succeeded = 0
    downloader = None
    music_manager = None
    exit_code = ExitCode.ERROR if failed_items else ExitCode.SUCCESS

    try:
        for index, url in enumerate(urls, 1):
            label = _track_label(index, len(urls)) if numbered or len(urls) > 1 else _track_label()
            if numbered or len(urls) > 1:
                click.echo(f"\n{'─' * 50}")
                click.echo(f"{label}: Processing {url}")
            logger.info(f"Processing URL: {url}")
            _track_status(logger, label, "Validating SoundCloud URL...")
            valid, message = URLValidator.validate_url(url)
            if not valid:
                failed_items.append((url, message))
                _track_status(logger, label, f"ERROR: {message}", fg="red", level="error")
                if not effective_continue:
                    # A validation abort is a usage error, unless processing already failed.
                    if exit_code == ExitCode.SUCCESS:
                        exit_code = ExitCode.USAGE
                    break
                exit_code = ExitCode.ERROR
                continue

            _track_status(logger, label, f"OK: Valid {message} URL", fg="green")
            if dry_run:
                _track_status(logger, label, "DRY-RUN: Would download track", fg="yellow")
                if open_music:
                    _track_status(
                        logger, label, "DRY-RUN: Would open with Apple Music", fg="yellow"
                    )
                if playlist_name:
                    _track_status(
                        logger,
                        label,
                        f"DRY-RUN: Would add to playlist '{playlist_name}'",
                        fg="yellow",
                    )
                succeeded += 1
                click.secho(f"{label}: DRY-RUN complete (no changes made)", fg="yellow", bold=True)
                continue

            if downloader is None:
                try:
                    downloader = _create_downloader(cfg, logger)
                except click.ClickException as exc:
                    failed_items.append((url, exc.message))
                    raise
            _track_status(logger, label, "Downloading track...")
            success, file_path, message = downloader.download(url)
            if not success or file_path is None:
                if success:
                    message = "Download finished, but the MP3 file could not be located."
                failed_items.append((url, message))
                exit_code = ExitCode.ERROR
                _track_status(logger, label, f"ERROR: {message}", fg="red", level="error")
                if not effective_continue:
                    break
                continue

            _track_status(logger, label, f"OK: {message}", fg="green")
            if open_music or playlist_name:
                if music_manager is None:
                    music_manager = AppleMusicManager()
                if open_music:
                    _track_status(logger, label, "Opening with Apple Music...")
                    success, message = music_manager.open_file_with_music(file_path)
                    _track_status(
                        logger,
                        label,
                        f"{'OK' if success else 'WARNING'}: {message}",
                        fg="green" if success else "yellow",
                        level="info" if success else "warning",
                    )
                if playlist_name:
                    _track_status(logger, label, f"Adding to playlist '{playlist_name}'...")
                    success, message = music_manager.add_to_playlist(file_path, playlist_name)
                    _track_status(
                        logger,
                        label,
                        f"{'OK' if success else 'WARNING'}: {message}",
                        fg="green" if success else "yellow",
                        level="info" if success else "warning",
                    )
            succeeded += 1
            click.secho(f"{label}: Done!", fg="green", bold=True)
    finally:
        _print_run_summary(logger, succeeded, len(failed_items), failed_items)

    if exit_code != ExitCode.SUCCESS:
        sys.exit(int(exit_code))


def _track_options(command):
    """Keep download and batch option names and defaults identical."""
    for option in reversed(
        [
            click.option(
                "--playlist",
                help="Playlist name; defaults to config. Pass an empty string to disable.",
            ),
            click.option(
                "--no-open/--open",
                default=None,
                help="Disable/enable automatic opening in Music. Defaults to config; playlist actions are independent.",
            ),
            click.option(
                "--continue-on-error/--stop-on-error",
                default=None,
                help="Continue/stop after an error. Defaults to config (stop).",
            ),
            click.option(
                "--dry-run",
                is_flag=True,
                help="Validate and preview without downloads, file writes, or Music actions.",
            ),
        ]
    ):
        command = option(command)
    return command


def _track_context(ctx, dry_run, playlist, no_open, continue_on_error):
    overrides = {}
    if playlist is not None:
        overrides["default_playlist"] = playlist
    if no_open is not None:
        overrides["open_music_app"] = not no_open
    if continue_on_error is not None:
        overrides["continue_on_error"] = continue_on_error
    return _context_state(ctx, log_to_file=not dry_run, overrides=overrides)


@cli.command()
@click.argument("urls", nargs=-1, required=True)
@_track_options
@click.pass_context
def download(
    ctx: click.Context,
    urls: Tuple[str, ...],
    playlist: Optional[str],
    no_open: Optional[bool],
    continue_on_error: Optional[bool],
    dry_run: bool = False,
):
    """Download one or more SoundCloud track URLs and import them into Apple Music."""
    state = _track_context(ctx, dry_run, playlist, no_open, continue_on_error)
    _run_tracks(
        state["config"], state["logger"], urls, playlist, no_open, continue_on_error, dry_run
    )


@cli.command()
@click.argument("batch_file", type=click.Path(exists=True, dir_okay=False, readable=True))
@_track_options
@click.pass_context
def batch(
    ctx: click.Context,
    batch_file: str,
    playlist: Optional[str],
    continue_on_error: Optional[bool],
    dry_run: bool = False,
    no_open: Optional[bool] = None,
):
    """Process a UTF-8 file of URLs, one per line. Blank lines and # comments are ignored.

    Invalid lines abort before downloading unless --continue-on-error is enabled.
    """
    state = _track_context(ctx, dry_run, playlist, no_open, continue_on_error)
    cfg, logger = state["config"], state["logger"]
    effective_continue = cfg.continue_on_error if continue_on_error is None else continue_on_error
    _, urls, errors = URLValidator.validate_batch_file(batch_file)
    for line_num, error in errors:
        click.secho(f"ERROR: Line {line_num}: {error}", fg="red", err=True)
        logger.error(f"Line {line_num}: {error}")
    if any(line == 0 for line, _ in errors):
        _exit_with_error(
            logger,
            "Batch file could not be read. Check the path, permissions, and UTF-8 encoding.",
            exit_code=int(ExitCode.USAGE),
        )
    if not urls:
        _exit_with_error(
            logger, "No valid URLs found in batch file.", exit_code=int(ExitCode.USAGE)
        )
    if errors and not effective_continue:
        _exit_with_error(
            logger,
            "Batch file validation failed. Fix the reported lines or use --continue-on-error to skip invalid URLs.",
            exit_code=int(ExitCode.USAGE),
        )
    click.secho(f"OK: Found {len(urls)} valid URL(s)", fg="green")
    _run_tracks(
        cfg,
        logger,
        tuple(urls),
        playlist,
        no_open,
        continue_on_error,
        dry_run,
        input_errors=[(f"line {line}", error) for line, error in errors],
        numbered=True,
    )


@cli.group()
def config():
    """Manage SC2AM configuration."""


@config.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing config")
@click.pass_context
def config_init(ctx: click.Context, force: bool):
    """Create defaults at --config PATH or ~/.sc2am/config.yaml.

    Existing files are preserved unless --force is specified. Does not load config
    or environment overrides, so it can repair an invalid configuration.
    """
    target = (ctx.obj.get("config_path") or ConfigManager.CONFIG_FILE).expanduser()
    existed = target.exists()
    try:
        config_path = ConfigManager.create_default_config(force=force, config_path=target)
    except OSError as exc:
        raise click.ClickException(
            f"Could not create configuration file: {target}. Check the path and permissions."
        ) from exc
    if existed and not force:
        click.echo(
            f"Configuration file already exists at: {config_path}. Use --force to overwrite."
        )
    else:
        click.secho(f"OK: Configuration file created at: {config_path}", fg="green")


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context):
    """Display effective settings after file, environment, and global CLI overrides."""
    cfg = _context_state(ctx, log_to_file=False)["config"]
    click.echo("\nCurrent Configuration:")
    click.echo("=" * 50)
    click.echo(f"Download Directory:  {cfg.download_dir}")
    click.echo(f"Music Library:       {cfg.music_library_path or '(auto-detect)'}")
    click.echo(f"Default Playlist:    {cfg.default_playlist or '(none)'}")
    click.echo(f"Keep Downloads:      {cfg.keep_downloads}")
    click.echo(f"Open Music App:      {cfg.open_music_app}")
    click.echo(f"Continue on Error:   {cfg.continue_on_error}")
    click.echo("\nWorkflow Settings:")
    click.echo(f"Normalize Metadata:  {cfg.normalize_metadata}")
    click.echo(f"Skip Existing:       {cfg.skip_existing_tracks}")
    click.echo(f"Log Level:           {cfg.log_level}")
    click.echo(f"Log File:            {cfg.log_file or '(console only)'}")
    click.echo("=" * 50)
    click.echo(
        "Compatibility settings (currently inactive): music_library_path, keep_downloads, normalize_metadata, skip_existing_tracks."
    )


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except Exception:
        logging.getLogger("sc2am").exception("Unhandled CLI error")
        click.secho(
            "ERROR: An unexpected error occurred. Please check the log file for details.",
            fg="red",
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
