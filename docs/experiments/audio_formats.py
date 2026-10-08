"""Reproduce the synthetic audio-format evaluation; no SoundCloud or Music access.

Run with Python 3 and ffmpeg, ffprobe and yt-dlp on PATH. The output directory
must not exist. This is a research utility, not a supported download command.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import wave


def run(root):
    root.mkdir(parents=True, exist_ok=False)
    rate = 44100
    rng = random.Random(91)
    with wave.open(str(root / "reference.wav"), "wb") as out:
        out.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        samples = bytearray()
        for i in range(rate * 30):
            t = i / rate
            envelope = 0.55 + 0.35 * math.sin(2 * math.pi * 1.7 * t)
            noise = rng.uniform(-0.07, 0.07)
            left = (
                envelope
                * (
                    0.28 * math.sin(2 * math.pi * 220 * t)
                    + 0.18 * math.sin(2 * math.pi * 880 * t)
                    + 0.10 * math.sin(2 * math.pi * (2000 * t + 80 * t * t))
                )
                + noise
            )
            right = (
                envelope
                * (
                    0.28 * math.sin(2 * math.pi * 330 * t)
                    + 0.18 * math.sin(2 * math.pi * 1320 * t)
                    + 0.10 * math.sin(2 * math.pi * (2400 * t + 90 * t * t))
                )
                - noise
            )
            samples.extend(struct.pack("<hh", round(left * 32767), round(right * 32767)))
        out.writeframes(samples)

    def encode(source, target, *options):
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(root / source),
                "-map",
                "0:a:0",
                *options,
                str(root / target),
            ],
            check=True,
        )

    encode("reference.wav", "source-mp3-128.mp3", "-c:a", "libmp3lame", "-b:a", "128k")
    encode("reference.wav", "source-aac-256.m4a", "-c:a", "aac", "-b:a", "256k")
    encode("source-mp3-128.mp3", "copy-mp3.mp3", "-c:a", "copy")
    encode("source-aac-256.m4a", "copy-aac.m4a", "-c:a", "copy")
    encode("source-aac-256.m4a", "wav-from-aac.wav", "-c:a", "pcm_s16le")
    encode("wav-from-aac.wav", "alac-from-aac.m4a", "-c:a", "alac", "-sample_fmt", "s16p")
    encode("reference.wav", "opus-64.opus", "-c:a", "libopus", "-b:a", "64k")
    encode("reference.wav", "flac.flac", "-c:a", "flac")

    # Use the same extraction flags as Downloader with explicitly local fixtures.
    # File URLs are enabled only here, never in the application download command.
    for ext, source, codec in [
        ("mp3", "source-mp3-128.mp3", "mp3"),
        ("m4a", "source-aac-256.m4a", "aac"),
    ]:
        info = root / f"local-{ext}.json"
        info.write_text(
            json.dumps(
                {
                    "id": f"local-{ext}",
                    "title": f"local-{ext}",
                    "url": (root / source).as_uri(),
                    "ext": ext,
                    "acodec": codec,
                    "vcodec": "none",
                    "extractor": "generic",
                    "extractor_key": "Generic",
                }
            )
        )
        subprocess.run(
            [
                "yt-dlp",
                "--enable-file-urls",
                "--ignore-config",
                "--no-playlist",
                "--format",
                "bestaudio/best",
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "192",
                "--output",
                str(root / "ytdlp-%(id)s.%(ext)s"),
                "--no-overwrites",
                "--load-info-json",
                str(info),
            ],
            check=True,
        )

    rows = []
    for path in sorted(root.iterdir()):
        if path.suffix not in {".wav", ".m4a", ".mp3", ".opus", ".flac"}:
            continue
        probe = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=codec_name,sample_rate,channels:format=duration",
                    "-of",
                    "json",
                    str(path),
                ]
            )
        )
        pcm = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-ac",
                "2",
                "-ar",
                str(rate),
                "-f",
                "s16le",
                "-c:a",
                "pcm_s16le",
                "-",
            ]
        )
        rows.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "codec": probe["streams"][0]["codec_name"],
                "pcm_bytes": len(pcm),
                "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            }
        )
    by_name = {row["file"]: row for row in rows}

    def digest(name):
        return by_name[name]["pcm_sha256"]

    assert digest("source-mp3-128.mp3") == digest("ytdlp-local-mp3.mp3")
    assert digest("source-aac-256.m4a") == digest("copy-aac.m4a")
    assert digest("source-aac-256.m4a") == digest("wav-from-aac.wav")
    assert digest("wav-from-aac.wav") == digest("alac-from-aac.m4a")
    assert digest("source-aac-256.m4a") != digest("ytdlp-local-m4a.mp3")
    assert digest("reference.wav") == digest("flac.flac")
    results = {
        "ffmpeg": subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0],
        "yt_dlp": subprocess.check_output(["yt-dlp", "--version"], text=True).strip(),
        "rows": rows,
    }
    (root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    run(parser.parse_args().output_dir.resolve())
