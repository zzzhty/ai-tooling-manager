"""Validate the documented OMH commands with the release parser, without running them."""
import argparse
from pathlib import Path
import shlex
import sys


def main():
    check = argparse.ArgumentParser(description=__doc__)
    check.add_argument("omh_source", type=Path, help="OMH v1.3.0 source checkout")
    check.add_argument("--guide", type=Path,
                       default=Path(__file__).resolve().parents[1] / "docs/HARNESS_USAGE.md")
    args = check.parse_args()
    sys.path.insert(0, str(args.omh_source.resolve()))
    from omh.standalone import build_parser

    parser = build_parser()
    parsed = []
    for number, line in enumerate(args.guide.read_text(encoding="utf-8").splitlines(), 1):
        tokens = line.strip()
        prefix = "python3 -B -m omh "
        if not tokens.startswith(prefix):
            continue
        try:
            parsed.append(parser.parse_args(shlex.split(tokens[len(prefix):], comments=True)))
        except SystemExit as error:
            raise SystemExit(f"{args.guide}:{number}: invalid OMH example: {tokens}") from error

    expected = {"status", "plan", "install", "refresh", "update", "uninstall", "recover"}
    if {item.command for item in parsed} != expected:
        raise SystemExit("The guide must exercise the full documented command set")
    if not any(item.command == "status" and item.skills_root for item in parsed):
        raise SystemExit("The guide must demonstrate exact-target status")
    print(f"Validated {len(parsed)} OMH examples (argument parsing only).")


if __name__ == "__main__":
    main()
