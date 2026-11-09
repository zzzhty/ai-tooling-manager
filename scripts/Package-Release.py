#!/usr/bin/env python3
"""Package the desktop application release (no distribution payload since ADR 0032)."""
import argparse
import platform
import shutil
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    suffix = ".exe" if sys.platform == "win32" else ""
    binary = repo / "target/release" / ("atm-desktop" + suffix)
    if not binary.is_file():
        parser.error(f"build the native release binary first: {binary}")
    destination = args.output.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(binary, destination / binary.name)
    icons = destination / "icons"
    icons.mkdir()
    names = ["icon.png", "icon.ico", "icon.icns"] + [
        f"icon-{size}.png" for size in (16, 20, 24, 32, 48, 64, 128, 256, 512, 1024)
    ]
    for name in names:
        shutil.copy2(repo / "apps/desktop/src-tauri/icons" / name, icons / name)
    shutil.copy2(repo / "LICENSE", destination / "LICENSE")
    (destination / "README.txt").write_text(
        "AI Tooling Manager (atm)\n\n"
        "Desktop application for the local vault, configuration preview/apply and quota queries.\n"
        "Skills and harness distribution is owned by OMH standalone; see its own repository.\n"
        "Keep atm-desktop and icons/ together when extracting or upgrading.\n"
        "This portable build is unsigned. Native desktop runtime requirements apply.\n"
        f"Platform: {sys.platform} {platform.machine()}\n", encoding="utf-8")
    archive = shutil.make_archive(str(destination), "zip" if sys.platform == "win32" else "gztar",
                                  destination.parent, destination.name)
    print(f"DISTRIBUTION_PACKAGE={archive}")


if __name__ == "__main__":
    main()
