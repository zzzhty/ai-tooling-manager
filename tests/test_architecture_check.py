"""The architecture checker catches recorded mistakes and accepts the current tree."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_architecture as arch

EMPTY = {"text_io_utf8": {}}

# eb5ced9, before the distribution smoke named UTF-8 for child-process text.
GIT_TEXT_RUN = """\
def run(*arguments, success=True):
    result = subprocess.run([str(cli), *arguments], cwd=root, env=env,
                            input="", text=True, capture_output=True, timeout=240)
    return result
"""

# b871816, before Package-Release.py passed encoding="utf-8" on verify-source.
VERIFY_SOURCE = """\
def verify(cli, payload):
    result = subprocess.run(
        [str(cli), "harness", "verify-source", "--source", str(payload)],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return result
"""

# scripts/Verify-MacOS.sh still reads the Tauri config with the locale encoding.
MACOS_CONFIG_READ = """\
import json
from pathlib import Path
config=json.loads(Path('apps/desktop/src-tauri/tauri.macos.conf.json').read_text())
"""

# scripts/Audit-TrackedSource.ps1 reads the manifest without -Encoding.
MANIFEST_READ = (
    "$manifest=Get-Content -LiteralPath (Join-Path $taskRoot 'scripts/source-manifest.json') "
    "-Raw | ConvertFrom-Json\n"
)

# bb32c35, before Linux smoke dropped the retired harness and skills fields.
LINUX_SMOKE = """\
python3 - "$atm_root/result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['passed'] and r['renderedVault'] and r['renderedQuotaUi'] and r['renderedHarnessUi'] and r['renderedSkillsUi'] and r['unknownVisible'] and r['demoQueryRendered'] and r['resized']
PY
"""

# 675f07c, before macOS smoke dropped the same fields and demoMutationRefused.
MACOS_SMOKE = """\
required = ["passed", "renderedVault", "renderedQuotaUi", "renderedHarnessUi", "renderedSkillsUi",
            "unknownVisible", "demoQueryRendered", "resized", "confirmedWrite", "confirmationRefused",
            "cancellationRefused", "duplicateRefused", "rollbackApplied", "capabilityDenied",
            "demoMutationRefused", "incognito"]
"""

SUCCESS_RESULT = """\
let result = serde_json::json!({
    "passed": true,
    "renderedVault": evidence.rendered_vault,
    "renderedQuotaUi": evidence.rendered_quota_ui,
    "unknownVisible": evidence.unknown_visible,
    "demoQueryRendered": evidence.demo_query_rendered,
    "resized": evidence.resized,
    "confirmedWrite": evidence.confirmed_write,
    "confirmationRefused": evidence.confirmation_refused,
    "cancellationRefused": evidence.cancellation_refused,
    "duplicateRefused": evidence.duplicate_refused,
    "rollbackApplied": evidence.rollback_applied,
    "capabilityDenied": evidence.capability_denied,
    "incognito": window_incognito
});
"""

# e031ae7, before safety.ts dropped the distribution error codes.
RETIRED_CODES = """\
export const messages = {
  HARNESS_NOT_INSTALLED: '未检测到可用的 harness 引擎安装；可在终端运行 atm harness bootstrap 后再次查询。',
  DEMO_READONLY: '演示模式不修改任何本机目录；请用真实模式管理技能。',
};
"""

# 7d38557, before current instructions stopped naming the retired tools.
RETIRED_TOOL = """\
先用 `Prepare-Content.py`
生成锁定的 OMH payload，再运行本地验证。内容作者测试由独立 OMH 仓库维护；ATM CI
当前 Rust 内容分发与显式交接 | [distribution](../crates/atm-core/src/distribution/)、[CLI 测试](../crates/atm-cli/tests/cli.rs)
"""

EXPLICIT_UTF8 = """\
import os
import subprocess
import tarfile
from pathlib import Path

def ok(path, archive):
    path.read_text(encoding="utf-8")
    path.read_text("utf-8")
    path.write_text("x", encoding="utf-8")
    open(path, "rb")
    open(path, "w", encoding="utf-8")
    fd = os.open(path, os.O_RDONLY)
    os.fdopen(fd, "wb")
    path.open("rb")
    tarfile.open(archive)
    subprocess.run(["git"], text=True, encoding="utf-8")
    subprocess.run(["git"], capture_output=True)
"""


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def errors(items, rule):
    return [item for item in items if item.level == "ERROR" and item.rule == rule]


class ArchitectureCheckTests(unittest.TestCase):
    def test_current_tree_has_no_errors(self) -> None:
        found = arch.check(ROOT, arch.load_baseline())
        self.assertEqual(
            [(item.path, item.line, item.violation) for item in found if item.level == "ERROR"],
            [],
        )

    def test_cli_passes_on_the_repository(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_architecture.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("[ARCH] Passed", completed.stdout)

    def test_distribution_smoke_text_mode_without_encoding_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "scripts/Test-Distribution.py", GIT_TEXT_RUN)
            caught = errors(arch.check(root, EMPTY), "text-io-utf8")
            self.assertEqual(len(caught), 1)
            self.assertIn('encoding="utf-8"', caught[0].fix)
            self.assertIn("eb5ced9", caught[0].principle)
            rendered = caught[0].render()
            self.assertIn("\n  Violation:", rendered)
            self.assertIn("\n  Fix:", rendered)
            self.assertIn("\n  Principle:", rendered)
            allowed = dict(EMPTY, text_io_utf8={"scripts/Test-Distribution.py": 1})
            self.assertEqual(errors(arch.check(root, allowed), "text-io-utf8"), [])

    def test_verify_source_text_mode_without_encoding_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "scripts/Package-Release.py", VERIFY_SOURCE)
            caught = errors(arch.check(root, EMPTY), "text-io-utf8")
            self.assertEqual(len(caught), 1)
            self.assertIn("b871816", caught[0].principle)
            self.assertIn('encoding="utf-8"', caught[0].fix)
            fixed = VERIFY_SOURCE.replace("text=True, timeout=60,", 'text=True, encoding="utf-8", timeout=60,')
            write(root, "scripts/Package-Release.py", fixed)
            self.assertEqual(errors(arch.check(root, EMPTY), "text-io-utf8"), [])

    def test_locale_config_read_and_manifest_get_content_follow_the_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "scripts/Verify-MacOS.sh", "python3 - <<'PY'\n" + MACOS_CONFIG_READ + "\nPY\n")
            write(root, "scripts/Audit-TrackedSource.ps1", MANIFEST_READ)
            allowed = {
                "text_io_utf8": {
                    "scripts/Verify-MacOS.sh": 1,
                    "scripts/Audit-TrackedSource.ps1": 1,
                }
            }
            self.assertEqual(errors(arch.check(root, allowed), "text-io-utf8"), [])
            # The shell heredoc and the PowerShell call are each one grandfathered site.
            # A second call in either file is a new violation.
            write(
                root,
                "scripts/Verify-MacOS.sh",
                "python3 - <<'PY'\n" + MACOS_CONFIG_READ + "\n" + MACOS_CONFIG_READ + "\nPY\n",
            )
            write(root, "scripts/Audit-TrackedSource.ps1", MANIFEST_READ + MANIFEST_READ)
            caught = errors(arch.check(root, allowed), "text-io-utf8")
            self.assertEqual(len(caught), 2)
            self.assertTrue(all("baseline allows 1" in item.violation for item in caught))
            self.assertTrue(all("architecture_baseline.json" in item.fix for item in caught))

    def test_explicit_utf8_binary_opens_and_tarfile_are_not_text_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "scripts/explicit.py", EXPLICIT_UTF8)
            write(root, "scripts/note.ps1", "# Get-Content readme.txt\nGet-Content -Encoding UTF8 readme.txt\n")
            self.assertEqual(errors(arch.check(root, EMPTY), "text-io-utf8"), [])

    def test_retired_linux_smoke_fields_are_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "apps/desktop/src-tauri/src/main.rs", SUCCESS_RESULT)
            write(root, "scripts/Test-LinuxGui.sh", LINUX_SMOKE)
            caught = errors(arch.check(root, EMPTY), "smoke-evidence")
            names = {item.violation.split("requires ", 1)[1].split(",", 1)[0] for item in caught}
            self.assertEqual(names, {"renderedHarnessUi", "renderedSkillsUi"})
            self.assertIn("bb32c35", caught[0].principle)
            self.assertIn("main.rs", caught[0].fix)
            rendered = caught[0].render()
            self.assertIn("\n  Violation:", rendered)
            self.assertIn("\n  Fix:", rendered)
            self.assertIn("\n  Principle:", rendered)

    def test_retired_macos_smoke_fields_are_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "apps/desktop/src-tauri/src/main.rs", SUCCESS_RESULT)
            write(root, "scripts/Test-MacOSGui.py", MACOS_SMOKE)
            caught = errors(arch.check(root, EMPTY), "smoke-evidence")
            names = {item.violation.split("requires ", 1)[1].split(",", 1)[0] for item in caught}
            self.assertEqual(names, {"renderedHarnessUi", "renderedSkillsUi", "demoMutationRefused"})
            self.assertIn("675f07c", caught[0].principle)

    def test_new_smoke_key_missing_from_the_result_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "apps/desktop/src-tauri/src/main.rs", SUCCESS_RESULT)
            write(root, "scripts/Test-LinuxGui.sh", "assert r['renderedPluginUi']\n")
            caught = errors(arch.check(root, EMPTY), "smoke-evidence")
            self.assertEqual(len(caught), 1)
            self.assertIn("renderedPluginUi", caught[0].violation)

    def test_retired_error_codes_and_tool_names_are_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "apps/desktop/src/safety.ts", RETIRED_CODES)
            write(root, "scripts/README.md", RETIRED_TOOL)
            write(root, "docs/adr/0032-note.md", RETIRED_TOOL)
            caught = errors(arch.check(root, EMPTY), "retired-distribution")
            self.assertTrue(any("HARNESS_NOT_INSTALLED" in item.violation for item in caught))
            self.assertTrue(any("DEMO_READONLY" in item.violation for item in caught))
            self.assertTrue(any("Prepare-Content" in item.violation for item in caught))
            self.assertTrue(any("atm-cli" in item.violation for item in caught))
            self.assertTrue(any(item.path.startswith("docs/") for item in caught))
            self.assertIn("e031ae7", caught[0].principle)
            self.assertIn("safety.ts", caught[0].fix)
            allowed = dict(EMPTY, retired_distribution={"docs/adr/0032-note.md": 2})
            remaining = errors(arch.check(root, allowed), "retired-distribution")
            self.assertTrue(all(not item.path.startswith("docs/") for item in remaining))
            self.assertTrue(any(item.path == "apps/desktop/src/safety.ts" for item in remaining))
            rendered = caught[0].render()
            self.assertIn("\n  Violation:", rendered)
            self.assertIn("\n  Fix:", rendered)
            self.assertIn("\n  Principle:", rendered)


if __name__ == "__main__":
    unittest.main()
