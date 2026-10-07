from click.testing import CliRunner

import main


def _doctor_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(main.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(main.platform, "release", lambda: "test-release")
    monkeypatch.setattr(main.platform, "python_version", lambda: "3.12.1")
    monkeypatch.setattr(main.importlib.metadata, "version", lambda _: "2026.7.4")
    monkeypatch.setattr(main.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        main.subprocess,
        "run",
        lambda command, **_: type(
            "Result", (), {"stdout": f"{command[0]} version 8.0", "stderr": "", "returncode": 0}
        )(),
    )
    monkeypatch.setattr(
        main.Path,
        "exists",
        lambda path: str(path) in {"/System/Applications/Music.app", str(tmp_path / "downloads")},
    )
    monkeypatch.setattr(main.Path, "is_dir", lambda path: str(path) == str(tmp_path / "downloads"))
    monkeypatch.setattr(main.os, "access", lambda *_: True)
    monkeypatch.setattr(
        main.ConfigManager,
        "get_config",
        lambda *_args, **_kwargs: type("Config", (), {"download_dir": tmp_path / "downloads"})(),
    )


def test_doctor_reports_read_only_prerequisite_status(monkeypatch, tmp_path):
    _doctor_environment(monkeypatch, tmp_path)
    result = CliRunner().invoke(main.cli, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "Platform: Darwin test-release" in result.output
    assert "Python: 3.12.1" in result.output
    assert "OK: yt-dlp: 2026.7.4" in result.output
    assert "OK: ffmpeg" in result.output
    assert "OK: ffprobe" in result.output
    assert "Music automation permission and runtime behavior are not tested" in result.output
    assert "Doctor: all checked prerequisites are available." in result.output


def test_doctor_returns_one_for_missing_tools_and_non_macos(monkeypatch, tmp_path):
    _doctor_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(main.platform, "system", lambda: "Linux")
    monkeypatch.setattr(main.shutil, "which", lambda _: None)
    result = CliRunner().invoke(main.cli, ["doctor"])

    assert result.exit_code == 1, result.output
    assert "WARN: ffmpeg: not found on PATH" in result.output
    assert "Music.app: available only on macOS" in result.output
    assert "Doctor: issues found." in result.output


def test_doctor_does_not_write_logs_or_touch_music(monkeypatch, tmp_path):
    _doctor_environment(monkeypatch, tmp_path)
    log_file = tmp_path / "logs" / "sc2am.log"
    monkeypatch.setenv("SC2AM_LOG_FILE", str(log_file))
    result = CliRunner().invoke(main.cli, ["doctor"])

    assert result.exit_code == 0, result.output
    assert not log_file.exists()
    assert not log_file.parent.exists()


def test_doctor_reports_invalid_configuration_as_problem(monkeypatch):
    monkeypatch.setattr(
        main.ConfigManager,
        "get_config",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(main.ConfigurationError("bad config")),
    )
    result = CliRunner().invoke(main.cli, ["doctor"])

    assert result.exit_code == 1, result.output
    assert "WARN: Configuration: bad config" in result.output
