"""Compare workflow calls/timing with simulated external latency; never accesses Music/network.

Run against this checkout or a baseline exported with git archive. The real CLI,
downloader, history and Music reconciliation execute; subprocesses and ID3 tagging
are replaced by deterministic doubles. Timings are synthetic, not real service speed.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner


class ExternalDouble:
    def __init__(self, download_dir, command_delay, extraction_delay):
        self.download_dir = download_dir
        self.command_delay = command_delay
        self.extraction_delay = extraction_delay
        self.counts = Counter()
        self.tracks = {}
        self.members = set()

    def run(self, command, **kwargs):
        time.sleep(self.command_delay)
        if command[0] == "yt-dlp":
            self.counts["yt_dlp_processes"] += 1
            metadata = "--dump-single-json" in command
            reused = "--load-info-json" in command
            if not reused:
                self.counts["url_extractions"] += 1
                time.sleep(self.extraction_delay)
                track_id = command[-1].rsplit("/", 1)[1]
                info = {"id": track_id, "title": track_id, "artist": "Fixture artist"}
            else:
                info = json.loads(Path(command[-1]).read_text())
                track_id = info["id"]
            if metadata:
                output = json.dumps(info)
            else:
                self.counts["audio_downloads"] += 1
                path = self.download_dir / f"{track_id} [{track_id}].mp3"
                path.write_bytes(b"isolated fixture audio")
                output = json.dumps(str(path))
        else:
            assert command[:2] == ["osascript", "-e"], command
            self.counts["music_processes"] += 1
            if len(command) == 3:
                self.counts["playlist_listings"] += 1
                output = '["Benchmark"]'
            else:
                path, playlist, marker, known, library, action, playlist_id = command[3:]
                if action == "resolve":
                    self.counts["target_resolutions" if path == "." else "library_resolutions"] += 1
                    output = "AAAAAAAAAAAAAAAA||CCCCCCCCCCCCCCCC|0"
                else:
                    track = self.tracks.get(marker, "")
                    if action == "import":
                        self.counts["music_mutations"] += 1
                        track = f"{len(self.tracks) + 1:016X}"
                        self.tracks[marker] = track
                    elif action == "playlist":
                        self.counts["music_mutations"] += 1
                        assert known == track
                        self.members.add(track)
                    output = "|".join(
                        [
                            "AAAAAAAAAAAAAAAA",
                            track,
                            "CCCCCCCCCCCCCCCC" if playlist else "",
                            "1" if playlist and track in self.members else "0",
                        ]
                    )
        return subprocess.CompletedProcess(command, 0, output, "")


def measure(cli_module, track_count, command_delay, extraction_delay):
    from sc2am.downloader import Downloader
    from sc2am.metadata import MetadataWriter

    with tempfile.TemporaryDirectory(prefix="sc2am-benchmark-") as directory:
        root = Path(directory)
        downloads = root / "downloads"
        urls = root / "urls.txt"
        urls.write_text(
            "\n".join(f"https://soundcloud.com/fixture/track{i}" for i in range(track_count))
        )
        cfg = SimpleNamespace(
            download_dir=downloads,
            open_music_app=False,
            default_playlist="Benchmark",
            continue_on_error=False,
        )
        external = ExternalDouble(downloads, command_delay, extraction_delay)
        args = ["batch", str(urls), "--no-open", "--playlist", "Benchmark", "--strict-import"]
        with (
            patch.object(
                cli_module, "_track_context", return_value={"config": cfg, "logger": Mock()}
            ),
            patch.object(Downloader, "_check_dependencies"),
            patch.object(MetadataWriter, "write_to_file", return_value=(True, "Mocked tags")),
            patch("subprocess.run", side_effect=external.run),
        ):
            results = []
            for phase in ("fresh", "resume"):
                external.counts.clear()
                start = time.perf_counter()
                result = CliRunner().invoke(cli_module.cli, args)
                elapsed = time.perf_counter() - start
                assert result.exit_code == 0, result.output
                assert f"Downloads: {track_count} succeeded, 0 failed" in result.output
                assert f"Playlists: {track_count} confirmed, 0 failed/unconfirmed" in result.output
                results.append({"phase": phase, "seconds": elapsed, "calls": dict(external.counts)})
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tracks", type=int, nargs="+", default=[1, 10])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--command-delay-ms", type=float, default=10)
    parser.add_argument("--extraction-delay-ms", type=float, default=20)
    args = parser.parse_args()
    if args.repeats < 1 or min(args.tracks) < 1:
        parser.error("tracks and repeats must be positive")
    sys.path.insert(0, str(args.checkout.resolve()))
    import main as cli_module

    rows = []
    for tracks in args.tracks:
        samples = [
            measure(
                cli_module, tracks, args.command_delay_ms / 1000, args.extraction_delay_ms / 1000
            )
            for _ in range(args.repeats)
        ]
        for index, phase in enumerate(("fresh", "resume")):
            counts = samples[0][index]["calls"]
            assert all(sample[index]["calls"] == counts for sample in samples)
            rows.append(
                {
                    "tracks": tracks,
                    "phase": phase,
                    "calls": counts,
                    "median_seconds": round(
                        statistics.median(s[index]["seconds"] for s in samples), 4
                    ),
                }
            )
    print(
        json.dumps(
            {
                "measurement": "simulated external latency, isolated CLI workflows",
                "command_delay_ms": args.command_delay_ms,
                "extraction_delay_ms": args.extraction_delay_ms,
                "repeats": args.repeats,
                "results": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
