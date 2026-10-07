"""Durable local evidence for download reuse and Music mutation reconciliation."""

from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Optional


class History:
    """A directory-local journal. Database errors must never silently reset it."""

    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.root = self.directory / ".sc2am"
        self.root.mkdir(exist_ok=True)
        self.connection = sqlite3.connect(self.root / "history.sqlite3", timeout=5)
        try:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self.connection.commit()
        except sqlite3.Error:
            self.connection.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.connection.close()

    def get(self, key: str) -> Any:
        row = self.connection.execute("SELECT value FROM records WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        if key.startswith(("source:", "file:")):
            self._validate_file_record(value)
        elif key.startswith("music:") and ":pending:" in key:
            if (
                not isinstance(value, dict)
                or value.get("stage") not in ("import", "playlist")
                or not isinstance(value.get("path"), str)
                or not isinstance(value.get("playlist"), str)
            ):
                raise RuntimeError("Invalid pending Music record; restore the history backup.")
        elif not isinstance(value, str) or not value:
            raise RuntimeError("Invalid identity in history; restore its backup.")
        return value

    def put(self, key: str, value: Any) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO records VALUES (?, ?)", (key, json.dumps(value))
            )

    def delete(self, key: str) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM records WHERE key = ?", (key,))

    @contextmanager
    def music_lock(self) -> Iterator[None]:
        """Serialize check/mutate/confirm across processes using this directory."""
        with (self.root / "music.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(
                    "Another Music import is running for this download directory. Try again when it finishes."
                ) from exc
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @staticmethod
    def fingerprint(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as audio:
            for chunk in iter(lambda: audio.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def remember_download(self, url: str, source: str, path: Path) -> None:
        record = {"path": str(path.resolve()), "digest": self.fingerprint(path), "source": source}
        self._put_many(
            {
                "file:" + str(path.resolve()): record,
                "source:" + source: record,
                "url:" + url: source,
            }
        )

    def cached_file(self, source: Optional[str]) -> Optional[Path]:
        if source is not None and not isinstance(source, str):
            raise RuntimeError("Invalid source identity in download history.")
        record = self.get("source:" + source) if source else None
        if not record:
            return None
        self._validate_file_record(record)
        path = Path(record["path"])
        if (
            path.parent == self.directory
            and path.suffix.lower() == ".mp3"
            and not path.is_symlink()
            and path.is_file()
        ):
            if self.fingerprint(path) != record["digest"]:
                raise RuntimeError(
                    "The cached MP3 changed; restore the verified file before retrying."
                )
            return path
        return None

    def file_source(self, path: Path) -> str:
        record = self.get("file:" + str(path.resolve()))
        digest = self.fingerprint(path)
        if record:
            self._validate_file_record(record)
            if record["digest"] != digest:
                raise RuntimeError(
                    "The MP3 changed since it was recorded. Restore the verified download before importing it."
                )
            return str(record["source"])
        source = "file:" + digest
        self.remember_download("", source, path)
        return source

    @staticmethod
    def _validate_file_record(record: Any) -> None:
        if not isinstance(record, dict) or not all(
            isinstance(record.get(key), str) and record[key] for key in ("path", "digest", "source")
        ):
            raise RuntimeError("Invalid file record in download history; restore its backup.")

    def refresh_file(self, path: Path, source: str) -> None:
        """Record our own ID3 marker edit without invalidating the audio cache."""
        record = {"path": str(path.resolve()), "digest": self.fingerprint(path), "source": source}
        self._put_many({"file:" + str(path.resolve()): record, "source:" + source: record})

    def _put_many(self, records: dict) -> None:
        with self.connection:
            self.connection.executemany(
                "INSERT OR REPLACE INTO records VALUES (?, ?)",
                [(key, json.dumps(value)) for key, value in records.items()],
            )
