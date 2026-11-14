"""Architecture rule implementations imported by scripts/check_architecture.py.

The entry command remains `python3 scripts/check_architecture.py`.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "artifacts",
    ".validation-cache",
    "dist",
}
# The denylist is defined here, and the tests quote the old snippets.
RETIRED_SKIP = frozenset({
    "scripts/architecture_rules.py",
    "tests/test_architecture_check.py",
})
TEXT_EXTENSIONS = {".py", ".sh"}
POWERSHELL_EXTENSION = ".ps1"
RETIRED_EXTENSIONS = {
    ".py", ".rs", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".sh", ".ps1",
    ".json", ".toml", ".html", ".css", ".yml", ".yaml", ".md",
}
SMOKE_RESULT = "apps/desktop/src-tauri/src/main.rs"
SMOKE_LINUX = "scripts/Test-LinuxGui.sh"
SMOKE_MACOS = "scripts/Test-MacOSGui.py"
SUBPROCESS_ATTRS = frozenset({
    "run", "check_output", "check_call", "Popen", "call", "getoutput", "getstatusoutput",
})
DISTINCT_SUBPROCESS_NAMES = frozenset({
    "check_output", "check_call", "Popen", "getoutput", "getstatusoutput",
})
GET_CONTENT = re.compile(r"(?i)(?<![-\\w])Get-Content\b")
PS_ENCODING = re.compile(r"(?i)(?<![-\\w])-Encoding\b")
HEREDOC = re.compile(r"<<'([A-Za-z_][A-Za-z0-9_]*)'\s*$")
ASSERTED_KEY = re.compile(
    r"""\b(?:r|result)\s*\[\s*['"]([A-Za-z][A-Za-z0-9]*)['"]\s*\]"""
)
JSON_KEY = re.compile(r'"([A-Za-z][A-Za-z0-9]*)"\s*:')

# Identifiers removed after ADR 0032 and then removed again from a live surface.
# e031ae7 dropped the error codes. bb32c35 and 675f07c dropped the smoke fields.
# 7d38557 dropped the tool names from live docs and ignore rules.
RETIRED_TOKENS = (
    "HARNESS_NOT_INSTALLED",
    "HARNESS_TIMEOUT",
    "HARNESS_RUNTIME",
    "HARNESS_CLI_FAILED",
    "HARNESS_PROTOCOL",
    "HARNESS_CONFIRMATION_REQUIRED",
    "HARNESS_BUSY",
    "HARNESS_UNSUPPORTED",
    "HARNESS_REQUEST",
    "HARNESS_OPERATION_FAILED",
    "HARNESS_HOME",
    "SKILLS_PROTECTED",
    "SKILLS_SOURCE",
    "SKILLS_UNAUDITABLE",
    "SKILLS_LIMIT",
    "SKILLS_NAME",
    "SKILLS_TAKEN",
    "SKILLS_FOREIGN_LINK",
    "SKILLS_ENGINE_LOCKED",
    "SKILLS_TRASH",
    "SKILLS_MISSING",
    "SKILLS_HOME",
    "DEMO_READONLY",
    "renderedHarnessUi",
    "renderedSkillsUi",
    "demoMutationRefused",
    "atm-cli",
    "Prepare-Content",
)

PRINCIPLES = {
    "text-io-utf8": (
        "Text reads and child-process output must name UTF-8. Locale decoding broke "
        "portable distribution smoke on a Windows legacy code page (eb5ced9), and the "
        "same text=True calls came back in the rewritten runner until they were given "
        "encoding=\"utf-8\" again (b871816)."
    ),
    "smoke-evidence": (
        "A GUI smoke assertion may require only keys the native success result records. "
        "After ADR 0032 removed the distribution UI, Linux still required renderedHarnessUi "
        "and renderedSkillsUi (bb32c35) and macOS still required those fields plus "
        "demoMutationRefused (675f07c)."
    ),
    "retired-distribution": (
        "Live code does not gain names from the skills/harness distribution surface ATM "
        "exited in ADR 0032. The same leftovers were deleted again from Linux smoke "
        "(bb32c35), macOS smoke (675f07c), current docs (7d38557), and the desktop error "
        "map (e031ae7). Dated history may keep the occurrences already in the baseline."
    ),
    "syntax": "The architecture check has to parse a source file before it can apply the other rules.",
}

TEXT_IO_FIX = {
    "read_text": (
        'Pass encoding="utf-8" to this Path.read_text call, or use read_bytes() when the '
        'caller decodes explicitly. Follow scripts/Test-Distribution.py.'
    ),
    "write_text": (
        'Pass encoding="utf-8" to this Path.write_text call. Follow scripts/Package-Release.py.'
    ),
    "open": (
        'Pass encoding="utf-8" to this open call unless the mode is binary. os.open is the '
        'file-descriptor syscall and is not a text read. Follow the UTF-8 contract in '
        "scripts/Test-Distribution.py."
    ),
    "subprocess": (
        'Pass encoding="utf-8" on this subprocess call. Child-process text that must survive '
        'a bad byte also passes errors="replace", as eb5ced9 did. Do not use text=True alone.'
    ),
    "get-content": (
        "Add -Encoding utf8 to this Get-Content call. The contract is the same explicit UTF-8 "
        'as Path.read_text(encoding="utf-8") in scripts/Test-Distribution.py.'
    ),
}

SMOKE_FIX = (
    "Drop that key from the smoke assertion, or record it on the success result in "
    "apps/desktop/src-tauri/src/main.rs (the serde_json::json! value with \"passed\": true). "
    "The Rust result is the authority. renderedHarnessUi, renderedSkillsUi, and "
    "demoMutationRefused are retired with ADR 0032 and must not return."
)

RETIRED_FIX = (
    "Delete this identifier. Skills and harness distribution belong to OMH standalone "
    "(ADR 0032). Do not map the code in apps/desktop/src/safety.ts, do not assert it from "
    "scripts/Test-LinuxGui.sh or scripts/Test-MacOSGui.py, and do not bring back "
    "atm-cli or Prepare-Content. Do not raise retired_distribution in "
    "scripts/architecture_baseline.json. Dated history keeps only the counts already listed."
)


@dataclass(frozen=True)
class Violation:
    level: str
    path: str
    line: int
    rule: str
    violation: str
    fix: str
    principle: str

    def render(self) -> str:
        return (
            f"[ARCH][{self.level}] {self.path}:{self.line}\n"
            f"  Violation: {self.rule}: {self.violation}\n"
            f"  Fix: {self.fix}\n"
            f"  Principle: {self.principle}\n"
        )


@dataclass(frozen=True)
class Site:
    line: int
    kind: str


def relpath(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def iter_files(root: Path, suffixes: set[str] | None = None) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if suffixes is None or path.suffix in suffixes:
                found.append(path)
    return found


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _encoding_provided(call: ast.Call, positional_index: int) -> bool:
    if _keyword(call, "encoding") is not None:
        return True
    return len(call.args) > positional_index


def _text_open_mode_index(func: ast.expr) -> int | None:
    """Positional index of the mode argument, or None when the call is not text open."""
    if isinstance(func, ast.Name) and func.id == "open":
        return 1
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr == "fdopen":
        return 1
    if func.attr != "open":
        return None
    receiver = func.value.id if isinstance(func.value, ast.Name) else None
    if receiver == "os":
        return None
    # Archive openers are binary containers, not locale text reads.
    if receiver in {"tarfile", "zipfile", "gzip", "bz2", "lzma"}:
        return None
    if receiver in {"io", "builtins"}:
        return 1
    return 0


def _mode_is_binary(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and "b" in node.value


def _is_subprocess_text(func: ast.expr, call: ast.Call) -> bool:
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        is_subprocess = func.value.id == "subprocess" and func.attr in SUBPROCESS_ATTRS
    elif isinstance(func, ast.Name):
        is_subprocess = func.id in DISTINCT_SUBPROCESS_NAMES
    else:
        is_subprocess = False
    if not is_subprocess:
        return False
    requested = False
    for name in ("text", "universal_newlines"):
        node = _keyword(call, name)
        if node is None:
            continue
        if isinstance(node, ast.Constant) and node.value is False:
            continue
        requested = True
    return requested and _keyword(call, "encoding") is None


def python_text_sites(source: str) -> list[Site]:
    tree = ast.parse(source)
    sites: list[Site] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"read_text", "write_text"}:
            index = 0 if func.attr == "read_text" else 1
            if not _encoding_provided(node, index):
                sites.append(Site(node.lineno, func.attr))
            continue
        mode_index = _text_open_mode_index(func)
        if mode_index is not None:
            mode = _keyword(node, "mode")
            if mode is None and len(node.args) > mode_index:
                mode = node.args[mode_index]
            encoding_index = 3 if mode_index == 1 else 2
            if not _mode_is_binary(mode) and not _encoding_provided(node, encoding_index):
                sites.append(Site(node.lineno, "open"))
            continue
        if _is_subprocess_text(func, node):
            sites.append(Site(node.lineno, "subprocess"))
    return sites


def shell_python_snippets(source: str) -> list[tuple[int, str]]:
    lines = source.splitlines()
    snippets: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = HEREDOC.search(lines[index])
        if not match:
            index += 1
            continue
        marker = match.group(1)
        start = index + 1
        end = start
        while end < len(lines) and lines[end] != marker:
            end += 1
        body = "\n".join(lines[start:end])
        if body:
            snippets.append((start + 1, body + "\n"))
        index = end + 1
    return snippets


def powershell_text_sites(source: str) -> list[Site]:
    logical: list[tuple[int, str]] = []
    buffer: list[str] = []
    start = 1
    for number, line in enumerate(source.splitlines(), 1):
        if not buffer:
            start = number
        buffer.append(line)
        if line.rstrip().endswith("`"):
            continue
        logical.append((start, "\n".join(buffer)))
        buffer = []
    if buffer:
        logical.append((start, "\n".join(buffer)))
    sites: list[Site] = []
    for number, chunk in logical:
        code = re.sub(r"(?m)#.*$", "", chunk)
        if GET_CONTENT.search(code) and not PS_ENCODING.search(code):
            sites.append(Site(number, "get-content"))
    return sites


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def text_io_sites(root: Path) -> tuple[dict[str, list[Site]], list[Violation]]:
    found: dict[str, list[Site]] = {}
    violations: list[Violation] = []
    for path in iter_files(root, TEXT_EXTENSIONS | {POWERSHELL_EXTENSION}):
        relative = relpath(root, path)
        source = _read(path)
        if path.suffix == ".py":
            pieces = [(1, source)]
        elif path.suffix == ".sh":
            pieces = shell_python_snippets(source)
        else:
            sites = powershell_text_sites(source)
            if sites:
                found[relative] = sites
            continue
        sites: list[Site] = []
        for base, snippet in pieces:
            try:
                parsed = python_text_sites(snippet)
            except SyntaxError as exc:
                violations.append(_violation(
                    "ERROR", relative, base + (exc.lineno or 1) - 1, "syntax",
                    f"Python syntax error: {exc.msg}",
                    "Fix the syntax error so the architecture check can read this file.",
                ))
                continue
            sites.extend(Site(base + site.line - 1, site.kind) for site in parsed)
        if sites:
            found[relative] = sites
    return found, violations


def _violation(level: str, path: str, line: int, rule: str, violation: str, fix: str) -> Violation:
    return Violation(level, path, line, rule, violation, fix, PRINCIPLES[rule])


def _mapping(baseline: dict[str, Any], key: str) -> dict[str, int]:
    value = baseline.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object of path to count")
    mapping: dict[str, int] = {}
    for path, count in value.items():
        if not isinstance(path, str) or isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(f"{key}[{path!r}] must be an integer count")
        if count < 0:
            raise ValueError(f"{key}[{path!r}] must be zero or greater")
        mapping[path] = count
    return mapping


def check_text_io(root: Path, baseline: dict[str, Any]) -> list[Violation]:
    allowed = _mapping(baseline, "text_io_utf8")
    found, violations = text_io_sites(root)
    for relative, sites in sorted(found.items()):
        ceiling = allowed.get(relative, 0)
        if len(sites) <= ceiling:
            continue
        if ceiling == 0:
            for site in sites:
                violations.append(_violation(
                    "ERROR", relative, site.line, "text-io-utf8",
                    f"Locale-dependent text call ({site.kind}) with no explicit encoding.",
                    TEXT_IO_FIX[site.kind],
                ))
            continue
        lines = ", ".join(str(site.line) for site in sites)
        violations.append(_violation(
            "ERROR", relative, max(site.line for site in sites), "text-io-utf8",
            f"{len(sites)} locale-dependent text calls; the baseline allows {ceiling} (lines {lines}).",
            "Pass encoding=\"utf-8\" on the new call. Do not increase text_io_utf8 for this file in "
            "scripts/architecture_baseline.json. Path text calls follow scripts/Test-Distribution.py "
            "and scripts/Package-Release.py; subprocess calls follow the encoding= fix in b871816; "
            "Get-Content takes -Encoding utf8.",
        ))
    return violations


def _matching_brace(source: str, open_index: int) -> int | None:
    depth = 0
    index = open_index
    while index < len(source):
        char = source[index]
        if char == '"':
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                    continue
                if source[index] == '"':
                    break
                index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def success_result_keys(source: str) -> tuple[int, set[str]] | None:
    """Keys of the native smoke success result, the object with \"passed\": true."""
    needle = "serde_json::json!("
    start = 0
    found: tuple[int, set[str]] | None = None
    while True:
        index = source.find(needle, start)
        if index < 0:
            return found
        brace = source.find("{", index)
        if brace < 0:
            return found
        end = _matching_brace(source, brace)
        if end is None:
            return found
        body = source[brace + 1:end]
        start = end + 1
        if not re.search(r'"passed"\s*:\s*true\b', body):
            continue
        line = source.count("\n", 0, brace) + 1
        found = (line, set(JSON_KEY.findall(body)))
    return found


def _asserted_keys_from_python(source: str) -> dict[str, int]:
    keys: dict[str, int] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            target = None
            value = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                value = node.value
            elif isinstance(node, ast.AnnAssign):
                target = node.target
                value = node.value
            if not isinstance(target, ast.Name) or target.id != "required" or value is None:
                continue
            if not isinstance(value, (ast.List, ast.Tuple)):
                continue
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    keys.setdefault(elt.value, elt.lineno)
    for match in ASSERTED_KEY.finditer(source):
        line = source.count("\n", 0, match.start()) + 1
        keys.setdefault(match.group(1), line)
    return keys


def asserted_smoke_keys(path: Path) -> dict[str, int] | None:
    if not path.is_file():
        return None
    source = _read(path)
    if path.suffix == ".py":
        return _asserted_keys_from_python(source)
    keys: dict[str, int] = {}
    for base, snippet in shell_python_snippets(source):
        for key, line in _asserted_keys_from_python(snippet).items():
            keys.setdefault(key, base + line - 1)
    for match in ASSERTED_KEY.finditer(source):
        line = source.count("\n", 0, match.start()) + 1
        keys.setdefault(match.group(1), line)
    return keys


def check_smoke_evidence(root: Path) -> list[Violation]:
    assertions = [(SMOKE_LINUX, root / SMOKE_LINUX), (SMOKE_MACOS, root / SMOKE_MACOS)]
    present = [(relative, path) for relative, path in assertions if path.is_file()]
    if not present:
        return []
    producer = root / SMOKE_RESULT
    if not producer.is_file():
        return [_violation(
            "ERROR", present[0][0], 1, "smoke-evidence",
            "Smoke assertions exist but the native success result is missing.",
            SMOKE_FIX,
        )]
    parsed = success_result_keys(_read(producer))
    if parsed is None:
        return [_violation(
            "ERROR", SMOKE_RESULT, 1, "smoke-evidence",
            'The native success result ("passed": true) could not be read.',
            SMOKE_FIX,
        )]
    _line, produced = parsed
    violations: list[Violation] = []
    for relative, path in present:
        keys = asserted_smoke_keys(path) or {}
        for key, line in sorted(keys.items(), key=lambda item: (item[1], item[0])):
            if key in produced:
                continue
            violations.append(_violation(
                "ERROR", relative, line, "smoke-evidence",
                f"Smoke assertion requires {key}, which the native success result does not record.",
                SMOKE_FIX,
            ))
    return violations


def _token_pattern(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


RETIRED_PATTERNS = tuple((token, _token_pattern(token)) for token in RETIRED_TOKENS)


def retired_sites(root: Path) -> dict[str, list[tuple[int, str]]]:
    found: dict[str, list[tuple[int, str]]] = {}
    for path in iter_files(root, RETIRED_EXTENSIONS):
        relative = relpath(root, path)
        if relative in RETIRED_SKIP:
            continue
        sites: list[tuple[int, str]] = []
        for line_number, line in enumerate(_read(path).splitlines(), 1):
            for token, pattern in RETIRED_PATTERNS:
                sites.extend((line_number, token) for _match in pattern.finditer(line))
        if sites:
            found[relative] = sites
    return found


def check_retired_distribution(root: Path, baseline: dict[str, Any]) -> list[Violation]:
    allowed = _mapping(baseline, "retired_distribution")
    violations: list[Violation] = []
    for relative, sites in sorted(retired_sites(root).items()):
        ceiling = allowed.get(relative, 0)
        if len(sites) <= ceiling:
            continue
        if ceiling == 0:
            for line_number, token in sites:
                violations.append(_violation(
                    "ERROR", relative, line_number, "retired-distribution",
                    f"Retired distribution identifier {token} is not allowed in this file.",
                    RETIRED_FIX,
                ))
            continue
        lines = ", ".join(str(line) for line, _token in sites)
        violations.append(_violation(
            "ERROR", relative, sites[-1][0], "retired-distribution",
            f"{len(sites)} retired distribution identifiers; the baseline allows {ceiling} (lines {lines}).",
            RETIRED_FIX,
        ))
    return violations


def retired_counts(root: Path) -> dict[str, int]:
    return {path: len(sites) for path, sites in sorted(retired_sites(root).items())}


def text_io_counts(root: Path) -> dict[str, int]:
    found, _violations = text_io_sites(root)
    return {path: len(sites) for path, sites in sorted(found.items())}
