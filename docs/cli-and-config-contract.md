# CLI and configuration contract

This document defines the public interface for the road to v2.0. Existing command
names, configuration keys, and environment variable names remain supported.

## Commands and options

The installed `sc2am` command and `python main.py` use the same entry point.
Global options go **before** the command; command options go after its name.

```text
sc2am [--config PATH] [--log-level LEVEL] download URL... [OPTIONS]
sc2am [--config PATH] [--log-level LEVEL] batch FILE [OPTIONS]
sc2am [--config PATH] config init [--force]
sc2am [--config PATH] [--log-level LEVEL] config show
```

`--help` is available at every command level. Help does not load configuration,
create log files, check download dependencies, or access Music.app.

`download` requires at least one SoundCloud track URL. `batch` requires a readable
UTF-8 text file containing one URL per line. Blank lines and lines beginning with
`#` after trimming whitespace are ignored. Inline comments are not supported.

Both processing commands accept exactly the same workflow options:

| Option | Behavior when supplied | Behavior when omitted |
| --- | --- | --- |
| `--playlist NAME` | Uses the trimmed name; `--playlist ""` disables playlist actions | Uses `default_playlist` |
| `--no-open` / `--open` | Disables / enables automatic opening in Music.app | Uses `open_music_app` |
| `--continue-on-error` / `--stop-on-error` | Continues / stops after a track error | Uses `continue_on_error` |
| `--dry-run` | Validates and previews actions without writing files, downloading, or accessing Music.app | Executes the workflow |

`--no-open` controls the automatic open step only. A requested playlist action can
still access Music.app. To disable both actions, use `--no-open --playlist ""`.
Dry runs also suppress configured log-file writes and do not require yt-dlp or
Music.app. Configuration and input validation still apply.

Direct URL runs validate and process URLs in order. Without continuation, they
stop at the first invalid URL or download failure; earlier downloads may already
have completed. Batch files are fully validated first. An invalid line aborts the
batch before downloads unless continuation is enabled. With continuation, invalid
lines are reported and skipped, and valid URLs are processed in file order.
Unreadable files and files with no valid URLs always abort.

## Configuration precedence

Values are merged in this order, from lowest to highest priority:

1. Built-in defaults.
2. The selected YAML file: `--config PATH`, or `~/.sc2am/config.yaml` when omitted.
3. Supported `SC2AM_*` environment variables.
4. Explicit CLI options.

A custom file **replaces** the default file; the two files are not merged. An
omitted default file is normal and uses built-in defaults. An explicitly selected
missing file is an error, except when creating it with `config init`.

An omitted CLI option never overrides configuration. For example, file or
environment `log_level: DEBUG` stays effective unless `--log-level` is supplied.
Boolean flags support both directions, so `--stop-on-error` overrides an
environment or YAML value of `true`.

Validation applies to the merged values: a higher-priority value may replace an
invalid lower-priority value for the same setting. The YAML document itself must
still be readable and well-formed. Unknown YAML keys are errors; unknown
environment variables are ignored. SC2AM reads the process environment and does
not automatically load `.env` files.

## Settings

| YAML key | Environment variable | Default | Effect |
| --- | --- | --- | --- |
| `download_dir` | `SC2AM_DOWNLOAD_DIR` | `~/Downloads/sc2am` | Destination for MP3 files |
| `default_playlist` | `SC2AM_PLAYLIST` | `null` | Optional Music playlist |
| `open_music_app` | `SC2AM_OPEN_MUSIC` | `true` | Automatically opens downloaded MP3s in Music |
| `continue_on_error` | `SC2AM_CONTINUE_ON_ERROR` | `false` | Continues after invalid entries or download failures |
| `log_level` | `SC2AM_LOG_LEVEL` | `INFO` | Logging threshold |
| `log_file` | `SC2AM_LOG_FILE` | `null` | Optional detailed log file |
| `music_library_path` | `SC2AM_MUSIC_LIBRARY` | `null` | Compatibility setting; currently inactive |
| `keep_downloads` | `SC2AM_KEEP_DOWNLOADS` | `true` | Compatibility setting; currently inactive |
| `normalize_metadata` | `SC2AM_NORMALIZE_METADATA` | `true` | Compatibility setting; currently inactive |
| `skip_existing_tracks` | `SC2AM_SKIP_EXISTING` | `false` | Compatibility setting; currently inactive |

The four compatibility settings remain accepted, validated, and displayed. They
do not currently change processing: Music uses its active library, downloaded
MP3s are retained, metadata tagging is always attempted, and SC2AM does not check
the Music library for existing tracks. Their presence does not promise these
features are implemented.

### Accepted values

- YAML must contain a mapping with string setting names. An empty file, YAML
  `null`, or `{}` uses defaults. Malformed YAML, other root types, unknown keys,
  invalid field values, and unreadable files produce actionable errors.
- Boolean strings accept `true`/`false`, `yes`/`no`, `on`/`off`, and `1`/`0`,
  ignoring case and surrounding whitespace. Native YAML booleans and `1`/`0`
  are also accepted. Other strings, including empty strings, are errors.
- Log levels accept `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL` without
  case sensitivity. Configuration values also allow surrounding whitespace.
- Path values expand `~` and environment variables for all three path settings.
  Relative paths are relative to the process working directory, including paths
  read from a custom config file. `download_dir` must not be empty or null.
- `music_library_path`, `log_file`, and `default_playlist` accept YAML `null`.
  Empty or whitespace-only strings also clear these optional settings, including
  environment overrides. Playlist names have surrounding whitespace removed.

### Inspecting and initializing

`config show` displays every effective setting after global overrides. It also
labels inactive compatibility settings. It does not create the configured log
file. Its human-readable display is not a machine-readable serialization format.

`config init` writes canonical defaults to the selected path and creates missing
parent directories. It reports an existing file without changing it. `--force`
replaces the file with defaults. Initialization does not load existing YAML or
apply environment overrides, so it can repair broken configuration:

```bash
sc2am config init --force
sc2am --config ./settings/sc2am.yaml config init
```

## Exit status and output

| Code | Meaning |
| --- | --- |
| `0` | Help, configuration operation, or processing completed without input/download failures |
| `1` | Runtime/setup failure, download failure, or a run that continued past invalid entries |
| `2` | Invalid CLI/configuration input, rejected batch file, or URL-validation abort |

If a continued run encounters both input and download failures, it returns `1`.
A direct run that has already encountered a download failure also returns `1`.
Continuation never converts a partial failure into success.

For compatibility, Music opening and playlist failures are warnings and do not
change exit status. Summary success counts refer to downloaded tracks (or valid
previews in a dry run), not confirmed Music imports. Failed or missing download
results count as failures. Items not attempted after stopping are not counted.

Progress and summaries are human-readable console output. Logger warnings and
errors, Click errors, and batch-line diagnostics go to stderr. Detailed logging
can be enabled through `log_file`; console logging suppresses informational
messages to avoid duplicating progress. Exact progress wording, colors, and
layout are not a machine-readable API; scripts should rely on exit status.

## Corrections from earlier behavior

The contract fixes unintended behavior: default CLI logging no longer masks YAML
or environment settings; malformed configuration and misspelled booleans no
longer silently fall back; single-track dry runs no longer download; batch input
errors now honor stop-on-error; `config init` can repair invalid config and
accurately reports preserved files. Correct previously ignored YAML key typos
before adopting this behavior.
