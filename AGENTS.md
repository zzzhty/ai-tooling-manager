# ATM repository instructions

- `crates/atm-core/src/application/` owns configuration preview/apply, templates and quota orchestration; CLI has been retired with ADR 0032 and the desktop app is the only frontend.
- Skills/harness distribution is owned by OMH standalone; ATM ships no distribution code, content lock or target policy. Handover follows the single-owner protocol in ADR 0031 (see ADR 0032 for the exit decision).
- Before changing identifiers or persisted contracts, read `docs/agents/internal-identifier-evolution.md`. Current operations are documented in `docs/HARNESS_USAGE.md`; retain historical ADRs and recovery data.
- Add tracked sources to `scripts/source-manifest.json`; artifacts, private configuration, caches and Home backups stay out of Git.

## Rules and what enforces them

After a change, run `python3 scripts/check_architecture.py` before finishing. CI runs that same command. It exits 1 on errors. Do not raise `scripts/architecture_baseline.json` to admit a new violation.

| Rule | Enforced by |
| --- | --- |
| Explicit UTF-8 on Python text calls and PowerShell `Get-Content` | `scripts/check_architecture.py` (`text-io-utf8`). A file may not exceed its count in the baseline. New calls use `encoding="utf-8"`: `scripts/Test-Distribution.py` and `scripts/Package-Release.py` for path text, and `encoding="utf-8"` on `subprocess` text (eb5ced9, b871816). `Get-Content` takes `-Encoding utf8`. |
| GUI smoke assertions require only keys recorded on the native success result | `scripts/check_architecture.py` (`smoke-evidence`). The authority is the `"passed": true` object in `apps/desktop/src-tauri/src/main.rs`. `scripts/Test-LinuxGui.sh` and `scripts/Test-MacOSGui.py` may not require a key that object does not record. |
| Retired distribution identifiers do not spread | `scripts/check_architecture.py` (`retired-distribution`). New files may not use the error codes, smoke fields, or tool names removed after ADR 0032 (bb32c35, 675f07c, 7d38557, e031ae7). Files that already name them are capped in the baseline. |
| Tracked source inventory | `scripts/Audit-TrackedSource.ps1` and the source audit inside `scripts/Verify-Local.sh`. Add files to `scripts/source-manifest.json`. |
| Rust formatting and lints | `cargo fmt --all --check` and `cargo clippy --locked --workspace --all-targets -- -D warnings` |
| Frontend types and tests | `npm run check` and `npm test` |
| Whitespace | `git diff --check` |
