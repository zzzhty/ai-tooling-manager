#!/usr/bin/env python3
"""Repository architecture checks. Local and CI run this same command.

    python3 scripts/check_architecture.py

Each finding prints Violation, Fix, and Principle. The script exits 1 when any
finding is an error. Grandfathered locale text calls live in
scripts/architecture_baseline.json. Do not raise that file to admit a new
violation.

The checker uses only the standard library. Rule bodies live in
architecture_rules.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from architecture_rules import (
    Violation,
    _mapping,
    _violation,
    check_retired_distribution,
    check_smoke_evidence,
    check_text_io,
    retired_counts,
    text_io_counts,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).resolve().parent / "architecture_baseline.json"


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("architecture baseline must be a JSON object")
    unknown = set(data) - {"notes", "text_io_utf8", "retired_distribution"}
    if unknown:
        raise ValueError(f"unknown architecture baseline keys: {sorted(unknown)}")
    _mapping(data, "text_io_utf8")
    _mapping(data, "retired_distribution")
    return data


def snapshot_baseline(root: Path | None = None) -> dict[str, Any]:
    """Current grandfathered text calls. Writing this over the baseline hides new violations."""
    root = REPO_ROOT if root is None else root
    return {
        "notes": (
            "Ratchet, not a waiver. text_io_utf8 and retired_distribution values are "
            "maximum counts allowed in that file. Do not raise an entry to land a new violation."
        ),
        "text_io_utf8": text_io_counts(root),
        "retired_distribution": retired_counts(root),
    }


def check(root: Path, baseline: dict[str, Any]) -> list[Violation]:
    violations = [
        *check_text_io(root, baseline),
        *check_smoke_evidence(root),
        *check_retired_distribution(root, baseline),
    ]
    violations.sort(key=lambda item: (item.path, item.line, item.rule, item.violation))
    return violations


def exit_code(violations: list[Violation]) -> int:
    return 1 if any(item.level == "ERROR" for item in violations) else 0


def main(argv: list[str] | None = None) -> int:
    if argv:
        raise SystemExit("python3 scripts/check_architecture.py takes no arguments")
    try:
        baseline = load_baseline()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        item = _violation(
            "ERROR", BASELINE_PATH.name, 1, "syntax",
            f"Architecture baseline could not be read: {exc}",
            "Restore scripts/architecture_baseline.json as the committed ratchet.",
        )
        print(item.render())
        print("[ARCH] Failed with 1 error(s), 0 warning(s).")
        return 1
    violations = check(REPO_ROOT, baseline)
    for item in violations:
        print(item.render())
    errors = sum(item.level == "ERROR" for item in violations)
    warnings = sum(item.level == "WARN" for item in violations)
    if errors:
        print(f"[ARCH] Failed with {errors} error(s), {warnings} warning(s).")
        return 1
    print(f"[ARCH] Passed with {warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
