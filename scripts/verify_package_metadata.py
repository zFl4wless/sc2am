"""Verify license metadata and files in built sdist and wheel artifacts."""

from __future__ import annotations

import email
import sys
import tarfile
import zipfile
from pathlib import Path


def check_metadata(metadata: bytes, artifact: Path) -> None:
    message = email.message_from_bytes(metadata)
    if message.get("License-Expression") != "MIT":
        raise SystemExit(f"{artifact.name}: expected License-Expression: MIT")


def verify_sdist(artifact: Path, expected_license: bytes) -> None:
    with tarfile.open(artifact, "r:gz") as archive:
        members = archive.getmembers()
        metadata = [
            member
            for member in members
            if member.name.endswith("/PKG-INFO") and member.name.count("/") == 1
        ]
        licenses = [
            member
            for member in members
            if member.name.endswith("/LICENSE") and member.name.count("/") == 1
        ]
        if len(metadata) != 1:
            raise SystemExit(f"{artifact.name}: expected one PKG-INFO file")
        check_metadata(archive.extractfile(metadata[0]).read(), artifact)
        if len(licenses) != 1 or archive.extractfile(licenses[0]).read() != expected_license:
            raise SystemExit(f"{artifact.name}: expected the repository LICENSE file")


def verify_wheel(artifact: Path, expected_license: bytes) -> None:
    with zipfile.ZipFile(artifact) as archive:
        metadata = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        licenses = [
            name for name in archive.namelist() if name.endswith(".dist-info/licenses/LICENSE")
        ]
        if len(metadata) != 1:
            raise SystemExit(f"{artifact.name}: expected one METADATA file")
        check_metadata(archive.read(metadata[0]), artifact)
        if len(licenses) != 1 or archive.read(licenses[0]) != expected_license:
            raise SystemExit(f"{artifact.name}: expected the repository LICENSE file")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_package_metadata.py DIST_DIRECTORY")
    dist = Path(sys.argv[1])
    sdists = list(dist.glob("*.tar.gz"))
    wheels = list(dist.glob("*.whl"))
    if len(sdists) != 1 or len(wheels) != 1:
        raise SystemExit(f"expected one sdist and one wheel in {dist}")

    expected_license = Path("LICENSE").read_bytes()
    verify_sdist(sdists[0], expected_license)
    verify_wheel(wheels[0], expected_license)
    print("Verified MIT license metadata and LICENSE contents in sdist and wheel.")


if __name__ == "__main__":
    main()
