# Isolated workflow measurements for #83

These are **simulated external-latency measurements**, not real SoundCloud,
FFmpeg or Music.app timings. No personal Music library was accessed. The real
CLI/batch loop, downloader, history, source marker and Music reconciliation run
against temporary files. Subprocesses and metadata tagging are mocked. Each
external command sleeps 10 ms; each simulated URL extraction sleeps another
20 ms. The double counts URL extraction for a URL-based yt-dlp command, but not
for loading checked JSON. Separate regression tests exercise actual yt-dlp
extraction and JSON loading with local file payloads, and verify real ID3 tags.

## Reproduce

Run from the repository root with the existing development environment:

```bash
.venv/bin/python scripts/benchmark_workflow.py
```

To compare the same harness against the baseline including merged PR #112,
export that commit into a temporary directory (no checkout changes required):

```bash
baseline_dir="$(mktemp -d)"
git archive 7cd24d3a17b5912d085fe87cb714b280282d0bd0 | tar -x -C "$baseline_dir"
.venv/bin/python scripts/benchmark_workflow.py --checkout "$baseline_dir"
```

Both commands use defaults of 1 and 10 tracks, 3 repeats and the above delays.
`--tracks`, `--repeats`, `--command-delay-ms` and `--extraction-delay-ms` override
these settings. The harness uses `batch --no-open --playlist Benchmark
--strict-import`, then repeats it against the same verified downloads and Music
state. Every repeat starts with a fresh temporary directory and fresh double.
The single/multiple URL entry point shares this loop; regression tests cover
both commands, unavailable targets, continuation and strict-import semantics.

## Recorded results

Recorded on 2026-10-07 with repository `.venv` (Python 3.14) on macOS.
Wall times are medians of three repetitions and include local orchestration,
SQLite/hash/marker work and the simulated delays. Counts were identical across
repetitions. They describe successful runs without external failures/retries.

| Tracks / phase | URL extractions, baseline → change | yt-dlp processes, baseline → change | Playlist listings, baseline → change | Music processes, baseline → change | Seconds, baseline → change |
| --- | --- | --- | --- | --- | --- |
| 1 fresh | 2 → 1 | 2 → 2 | 1 → 1 | 6 → 7 | 0.1622 → 0.1520 |
| 1 resume | 0 → 0 | 0 → 0 | 1 → 1 | 3 → 4 | 0.0414 → 0.0561 |
| 10 fresh | 20 → 10 | 20 → 20 | 10 → 1 | 60 → 52 | 1.5271 → 1.3234 |
| 10 resume | 0 → 0 | 0 → 0 | 10 → 1 | 30 → 22 | 0.4205 → 0.3283 |

The change adds one read-only target-ID resolution per run after listing names.
This creates overhead for a single resumed track. For ten tracks, it eliminates
nine name-list queries while adding one ID-resolution query. Per-track live ID,
writability and membership checks remain necessary. Successful fresh runs still
perform two Music mutations per track; resumed confirmed runs perform none.
Download subprocess count stays at two per fresh track, while the duplicate URL
extraction is removed. Real network, signed media expiry, FFmpeg, artwork,
library size, Music responsiveness and process startup can dominate real runs;
no end-to-end real-world acceleration has been measured or claimed.

Collections and failed preflights stop before audio downloads. Temporary audio
retries reuse the checked JSON and clean it up afterwards. Failed media URLs
cannot trigger an unchecked URL re-extraction. Exact known URLs resume without
yt-dlp or retagging, including after Music failures. Uncertain Music mutations
remain pending and are reconciled by reads rather than replayed. Missing,
ambiguous, non-writable and stale playlist targets retain MP3s and report the
failed stage explicitly. A new run resolves the target again.
