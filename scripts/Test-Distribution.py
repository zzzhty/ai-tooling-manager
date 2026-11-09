#!/usr/bin/env python3
"""Verify an extracted desktop-only release offline: layout, icons, README, no payload."""
import argparse
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ICONS = ["icon.png", "icon.ico", "icon.icns"] + [
    f"icon-{size}.png" for size in (16, 20, 24, 32, 48, 64, 128, 256, 512, 1024)
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve(strict=True)
    root = Path(tempfile.mkdtemp(prefix="atm-package-test-"))
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(root)
    else:
        with tarfile.open(archive) as bundle:
            bundle.extractall(root, filter="data")
    children = [path for path in root.iterdir() if path.is_dir()]
    assert len(children) == 1, "archive must contain exactly one top-level directory"
    extracted = children[0]
    binary = extracted / ("atm-desktop.exe" if sys.platform == "win32" else "atm-desktop")
    assert binary.is_file() and binary.stat().st_size > 1_000_000, "desktop executable missing"
    for name in ICONS:
        assert (extracted / "icons" / name).is_file(), f"icon missing: {name}"
    assert (extracted / "LICENSE").is_file()
    readme = (extracted / "README.txt").read_text(encoding="utf-8")
    assert "OMH standalone" in readme
    assert not (extracted / "harness").exists(), "release must not embed a distribution payload"
    assert not any(path.name == "atm" for path in extracted.iterdir()), "CLI is retired with ADR 0032"
    print("DISTRIBUTION_SMOKE=PASS: extracted desktop-only release (executable, icons, license, readme, no payload)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
