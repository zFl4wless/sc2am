"""Run with a fresh package venv's Python and -I, outside the source checkout."""

import os
from importlib.metadata import distribution
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import main
import sc2am


def smoke():
    prefix = Path(sys.prefix).resolve()
    for module in (main, sc2am):
        assert Path(module.__file__).resolve().is_relative_to(prefix), module.__file__
    package = distribution("sc2am")
    assert package.version == sc2am.__version__, package.version
    entry = next(entry for entry in package.entry_points if entry.name == "sc2am")
    assert entry.group == "console_scripts" and entry.value == "main:main", entry
    executable = Path(sys.executable).parent / "sc2am"
    assert executable.is_file(), executable

    with TemporaryDirectory(prefix="sc2am-smoke-") as directory:
        root = Path(directory)
        env = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith(("SC2AM_", "PYTHON"))
        }
        env["HOME"] = str(root)
        env["SC2AM_DOWNLOAD_DIR"] = str(root / "downloads")
        env["SC2AM_LOG_FILE"] = str(root / "logs" / "sc2am.log")

        def run(*args, code=0, expected):
            result = subprocess.run(
                [str(executable), *args],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            assert result.returncode == code, output
            assert expected in output, output

        run("--help", expected="Usage:")
        run("config", "init", expected="Configuration file created")
        config_path = root / ".sc2am" / "config.yaml"
        assert config_path.is_file()
        config_path.write_text("default_playlist: Kept until explicit reset\n", encoding="utf-8")
        run("config", "init", expected="Use --force to overwrite")
        assert config_path.read_text(encoding="utf-8") == (
            "default_playlist: Kept until explicit reset\n"
        )

        # Configuration repair must not remove the separate resume journal.
        history = root / "downloads" / ".sc2am" / "history.sqlite3"
        history.parent.mkdir(parents=True)
        history.write_bytes(b"isolated smoke fixture")
        run("config", "init", "--force", expected="Configuration file created")
        assert "Kept until explicit reset" not in config_path.read_text(encoding="utf-8")
        assert history.read_bytes() == b"isolated smoke fixture"

        run("config", "show", expected="Current Configuration:")
        url = "https://soundcloud.com/artist/track"
        run("download", url, "--dry-run", expected="1 succeeded, 0 failed")
        batch = root / "urls.txt"
        batch.write_text(f"# Smoke test\n{url}\n", encoding="utf-8")
        run("batch", str(batch), "--dry-run", expected="1 succeeded, 0 failed")
        run(
            "download",
            "invalid",
            "--dry-run",
            code=2,
            expected="0 succeeded, 1 failed",
        )
        assert list((root / "downloads").iterdir()) == [history.parent]
        assert not list((root / "downloads").glob("*.mp3"))
        assert not (root / "logs").exists()

    if sys.platform == "darwin":
        # Exercise the native AppleScript runtime without launching Music or logging in.
        result = subprocess.run(
            ["osascript", "-e", 'return "sc2am-smoke"'],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.stdout.strip() == "sc2am-smoke", result.stdout
    print(f"Installed SC2AM {package.version} smoke passed on {sys.platform}")


if __name__ == "__main__":
    smoke()
