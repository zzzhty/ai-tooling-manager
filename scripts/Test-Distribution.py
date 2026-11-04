#!/usr/bin/env python3
"""Exercise an extracted native distribution offline with no Python on its PATH.

The test runner uses Python; the tested CLI gets an empty PATH and a fake home.
The optional runtime smoke prepares disposable venvs through OMH's provider.
No real accounts, installations, configuration or network are used.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def read_content_manifest(source: Path) -> dict:
    content = json.loads((source / "content-manifest.json").read_text(encoding="utf-8"))
    lock = json.loads((source / "content-lock.json").read_text(encoding="utf-8"))
    return {**content, "files": lock["files"], "directories": lock["directories"]}


def verify_runtime_payload(cache: Path, manifest: dict, identity: str, env: dict, root: Path):
    """Validate the copied runtime and Rust snapshot without preparing any venv."""
    catalog = json.loads((cache / "canonical-catalog.json").read_text(encoding="utf-8"))
    assert catalog["sourceIdentity"] == identity
    assert catalog["schemaVersion"] == 1
    assert catalog["product"] == "atm-harness-catalog"
    for skill in catalog["skills"]:
        assert (cache / skill["path"] / "SKILL.md").is_file()
    for overlay in catalog["attributionOverlays"]:
        assert json.loads((cache / overlay["path"]).read_text(encoding="utf-8")) == overlay["data"]
    for group in manifest["runtimeGroups"]:
        lock = group.get("requirementsLock")
        if lock:
            assert (cache / lock).is_file()
            assert "--hash=sha256:" in (cache / lock).read_text(encoding="utf-8")
    ids = {skill["id"] for skill in catalog["skills"]}
    assert set(manifest["runtimeBindings"]) <= ids
    assert not any(key.startswith("hook:") for key in manifest["runtimeBindings"])
    for entry in manifest["files"]:
        if entry["path"].endswith(".py"):
            ast.parse((cache / entry["path"]).read_text(encoding="utf-8"), filename=entry["path"])
    assert not (cache / "scripts").exists()
    assert not (cache / "runtimes/watcher").exists()
    assert catalog["attributionOverlays"] == []
    assert manifest["historicalIdentities"] == {}
    assert "maintenance:doc-alignment" in ids
    assert "mattpocock-skills:writing-for-agents" in ids
    assert not any("skill-maintainer" in name or name.startswith("watcher:") for name in ids)
    assert {group["id"] for group in manifest["runtimeGroups"]} == {"maintenance", "workflow"}
    before = {path.relative_to(root) for path in root.rglob("*")}
    skill = next(skill for skill in catalog["skills"] if skill["id"] == "maintenance:doc-alignment")
    script = cache / skill["path"] / "scripts/audit_docs.py"
    subprocess.run([sys.executable, "-S", "-B", str(script), "--help"], cwd=root, env=env,
                   capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
    assert {path.relative_to(root) for path in root.rglob("*")} == before, "read-only payload check wrote files"
    print(f"DISTRIBUTION_PAYLOAD=PASS: {len(catalog['skills'])} catalog entries, skill-owned helpers, no venv/hooks", flush=True)


def verify_shared_runtime(cli: Path, env: dict, root: Path):
    """Run the selected OMH provider through ATM and persistent launchers."""
    def run(*arguments):
        result = subprocess.run([str(cli), *arguments], cwd=root, env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=120)
        if result.returncode:
            raise RuntimeError(f"{arguments}: {result.stdout}\n{result.stderr}")
        return json.loads(result.stdout)

    user = Path(env["HOME"])
    deployment = root / "runtime storage 空间"
    run("install", "skills", "--harness", "claude-code")
    prepared = {}
    for group in ("maintenance", "workflow"):
        prepared[group] = run("harness", "runtime", "prepare", group, "--python",
            str(Path(sys.executable).resolve()), "--deployment-root", str(deployment), "--offline")["prepared"]
        assert Path(prepared[group]["root"]).is_relative_to(deployment)
    binding = user / ".claude/.omh-runtime"
    if os.name == "nt":
        shell = shutil.which("powershell") or shutil.which("pwsh")
        assert shell, "native PowerShell is required to check the Windows launcher"
        command = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(binding / "run.ps1")]
    else:
        command = ["/bin/sh", str(binding / "run.sh")]

    def launch(group, script, *arguments, child_env=env):
        return subprocess.run([*command, group, str(script), *arguments], cwd=root, env=child_env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=30)

    for skill, helper, group in (
        ("doc-alignment", "audit_docs.py", "maintenance"),
        ("long-running-goal", "check_goal_ready.py", "workflow"),
        ("sop", "check_sop_ready.py", "workflow"),
        ("summary-in-html", "collect_summary_inputs.py", "workflow"),
    ):
        result = launch(group, user / ".claude/skills" / skill / "scripts" / helper, "--help")
        assert result.returncode == 0, (skill, result.stdout, result.stderr)
    probe = root / "argv helper 空间.py"
    probe.write_text("import json,sys; print(json.dumps({'prefix':sys.prefix,'argv':sys.argv[1:]}))\n", encoding="utf-8")
    arguments = ["space arg", "中文", "", '"quote"', "$(no shell)", "C:\\path with spaces\\"]
    result = launch("workflow", probe, *arguments)
    assert result.returncode == 0, (result.stdout, result.stderr)
    actual = json.loads(result.stdout)
    assert actual["argv"] == arguments
    assert Path(actual["prefix"]).resolve() == Path(prepared["workflow"]["root"]).resolve()
    invalid = launch("workflow", probe, child_env={**env, "OMH_PYTHON": str(root / "missing interpreter")})
    assert invalid.returncode != 0, "invalid explicit interpreter silently fell back"
    assert not (user / ".oh-my-harness").exists(), "ATM created an OMH standalone manager"
    run("uninstall", "skills", "--harness", "claude-code")
    assert all(Path(item["root"]).is_dir() for item in prepared.values())
    print("DISTRIBUTION_RUNTIME=PASS: selected provider, explicit deployment, both groups, four helpers, "
          "persistent launchers, argv, invalid override and retained venvs", flush=True)



def main():
    # Native command JSON and CI logs use UTF-8 even with a Windows legacy locale.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, nargs="?")
    parser.add_argument("--payload-only", type=Path, help="check a verified payload with an isolated runner")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--cli-only", action="store_true", help="validate an official CLI-only archive without a desktop executable")
    parser.add_argument("--runtime-smoke", action="store_true", help="prepare isolated OMH runtimes and execute installed helpers")
    args = parser.parse_args()
    if args.payload_only:
        if not args.cli:
            parser.error("--payload-only requires --cli")
        source = args.payload_only.resolve()
        with tempfile.TemporaryDirectory(prefix="ATM_TEST_ONLY_payload_") as temporary:
            root = Path(temporary).resolve()
            # Keep the runtime's module cache location: omitting it makes an
            # isolated Windows PowerShell repeat expensive startup analysis.
            env = {key: value for key, value in os.environ.items()
                   if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PSMODULEANALYSISCACHEPATH"}}
            env.update(PATH="", HOME=str(root), USERPROFILE=str(root), ATM_HOME=str(root / 'manager'))
            result = subprocess.run([str(args.cli.resolve()), 'harness', 'bootstrap', '--source', str(source)],
                                    env=env, capture_output=True, text=True, encoding='utf-8', check=True)
            status = json.loads(result.stdout)
            verify_runtime_payload(Path(status['manager']['repository']), read_content_manifest(source),
                                   status['manager']['revision'], env, root)
            if args.runtime_smoke:
                verify_shared_runtime(args.cli.resolve(), env, root)
        return
    if args.archive is None:
        parser.error("archive or --payload-only is required")
    with tempfile.TemporaryDirectory(prefix="atm distribution Unicode 测试 ") as temporary:
        # macOS's default /var temporary path is a system symlink. Keep the
        # tested payload and manager paths physical without relaxing ownership.
        root = Path(temporary).resolve()
        extracted = root / "extracted"
        shutil.unpack_archive(args.archive.resolve(), extracted)
        package, = extracted.iterdir()
        cli = package / ("atm.exe" if os.name == "nt" else "atm")
        desktop = package / ("atm-desktop.exe" if os.name == "nt" else "atm-desktop")
        if args.cli_only:
            assert not desktop.exists(), "desktop binary leaked into CLI-only package"
            assert not (package / "icons").exists(), "desktop icons leaked into CLI-only package"
        else:
            assert desktop.is_file(), "desktop binary missing from release archive"
            icons = package / "icons"
            for size in (16, 20, 24, 32, 48, 64, 128, 256, 512, 1024):
                data = (icons / f"icon-{size}.png").read_bytes()
                assert data[:8] == b"\x89PNG\r\n\x1a\n"
                assert [int.from_bytes(data[i:i+4], "big") for i in (16, 20)] == [size, size]
            assert (icons / "icon.png").read_bytes() == (icons / "icon-256.png").read_bytes()
            assert (icons / "icon.ico").read_bytes()[:6] == b"\x00\x00\x01\x00\x08\x00"
            assert (icons / "icon.icns").read_bytes()[:4] == b"icns"

        user = root / "user"
        user.mkdir()
        home = user / "manager with spaces"
        env = {key: value for key, value in os.environ.items()
               if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PSMODULEANALYSISCACHEPATH"}}
        env.update(PATH="", HOME=str(user), USERPROFILE=str(user), ATM_HOME=str(home),
                   APPDATA=str(user / "appdata"), LOCALAPPDATA=str(user / "localappdata"),
                   XDG_DATA_HOME=str(user / ".local/share"), XDG_CONFIG_HOME=str(user / ".config"))

        def run(*arguments, success=True, program=cli):
            print("DISTRIBUTION_STEP=" + program.name + " " + " ".join(arguments), flush=True)
            result = subprocess.run([str(program), *arguments], cwd=root, env=env,
                stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=120)
            if (result.returncode == 0) != success:
                raise RuntimeError(f"{arguments}: exit {result.returncode}\n"
                                   f"{result.stdout[-10000:]}\n{result.stderr[-10000:]}")
            return result

        run("help")
        run("harness", "status", "--json")
        assert not home.exists(), "read-only status created a manager home"
        invalid = run("harness", "bootstrap", "--home", "relative-manager-home", success=False)
        assert "CLI_ARGUMENT" in invalid.stderr and not home.exists()
        source = package / "harness"
        assert not (source / "scripts").exists(), "installer scripts leaked into payload"
        assert not (source / "tests").exists()
        source_info = json.loads(run("harness", "verify-source").stdout)
        manifest = read_content_manifest(source)
        actual = {path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file()}
        assert actual == {entry["path"] for entry in manifest["files"]} | {"content-manifest.json", "content-lock.json"}
        if not args.cli_only:
            resources = json.loads(run("--verify-distribution", program=desktop).stdout)
            assert resources["releaseBuild"] and not resources["guiInitialized"] and not resources["storageInitialized"]
            assert resources["sourceIdentity"] == source_info["identity"]
            assert Path(resources["sourceRoot"]) == source.resolve()
            assert "/index.html" in resources["frontendAssets"]
            assert not home.exists(), "desktop resource probe initialized storage"
            print("DISTRIBUTION_RESOURCES=" + json.dumps(resources, ensure_ascii=False, sort_keys=True), flush=True)
            print("DISTRIBUTION_DESKTOP=PASS: embedded HTML/JS/CSS and adjacent verified payload; no GUI/storage initialized", flush=True)
        env["ATM_HOME"] = str(user / "unused-manager")
        run("harness", "bootstrap", "--home", str(home))
        assert not Path(env["ATM_HOME"]).exists()
        env["ATM_HOME"] = str(home)
        status = json.loads(run("harness", "status", "--json").stdout)
        cache = Path(status["manager"]["repository"])
        assert status["runtimes"] == {} and not status["hooksEnabled"]
        verify_runtime_payload(cache, manifest, source_info["identity"], env, root)
        assert not (home / "venv").exists() and not (home / "runtimes").exists()
        run("harness", "plan", "install", "--harness", "zcode")
        assert not (user / ".zcode").exists(), "plan changed the target"
        # The full local cache must support every static operation offline.
        hidden = package / "hidden-harness"
        source.rename(hidden)
        try:
            assert "HARNESS_SOURCE_MISSING" in run("harness", "verify-source", success=False).stderr
            if not args.cli_only:
                assert "HARNESS_SOURCE_MISSING" in run("--verify-distribution", program=desktop, success=False).stderr
            run("install", "skills", "--harness", "zcode")
            run("update", "skills", "--harness", "zcode")
            run("check", "skills", "--harness", "zcode")
            codex = user / ".codex"
            codex.mkdir()
            codex_config = codex / "config.toml"
            codex_config.write_text('theme = "TEST_ONLY user setting"\n', encoding="utf-8")
            run("install", "skills", "--harness", "codex")
            run("update", "skills", "--harness", "codex")
            run("check", "skills", "--harness", "codex")
            run("uninstall", "skills", "--harness", "codex")
            assert 'theme = "TEST_ONLY user setting"' in codex_config.read_text(encoding="utf-8")
            config = user / ".zcode/user-config.json"
            config.write_text('{"testOnly":"preserve"}\n', encoding="utf-8")
            instructions = user / ".zcode/AGENTS.md"
            original = instructions.read_bytes()
            instructions.write_bytes(original + b"\nTEST_ONLY user modification\n")
            run("update", "skills", "--harness", "zcode", success=False)
            run("uninstall", "skills", "--harness", "zcode", success=False)
            assert instructions.read_bytes().endswith(b"TEST_ONLY user modification\n")
            instructions.write_bytes(original)
            status = json.loads(run("harness", "status", "--json").stdout)
            assert status["product"] == "atm-harness"
            run("uninstall", "skills", "--harness", "zcode")
            assert config.read_text(encoding="utf-8") == '{"testOnly":"preserve"}\n'
            assert not instructions.exists()
        finally:
            hidden.rename(source)
        run("harness", "sync")
        scope = "extracted CLI-only release" if args.cli_only else "complete extracted release (CLI lifecycle + desktop resources + runtime payload)"
        print(f"DISTRIBUTION_SMOKE=PASS: {scope}, empty PATH, offline cache, Unicode/spaces, "
              "plan/apply, native Codex projection, status, user-edit conflict and configuration preservation")
        if args.runtime_smoke:
            verify_shared_runtime(cli, env, root)


if __name__ == "__main__":
    main()
