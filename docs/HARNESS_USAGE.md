# Harness content and manager workflow

ATM installs versioned OMH content through the Rust distribution service. It
supports inert import, explicit source selection, preview/apply, owned runtimes
and recovery. It does not maintain a skill Hub or an independent Python installer.
`content/omh.lock.json` pins the release; target paths come from `policy/harnesses`.

For a source checkout run `python scripts/Prepare-Content.py` before tests or
packaging. This builds `atm-cli` and uses its locked fetch/validator to materialize
ignored `harness/`. Existing complete content works offline. An unexpected or
stale destination is refused; preserve it and prepare the new payload in an empty
location instead of silently overwriting it. Complete portable releases retain
CLI, desktop and verified payload together; CLI-only packages retain just `atm`,
the same verified payload and license/readme. Neither mode installs Python for
static distribution.

## Independent versions and CLI-only packages

ATM application 0.2.0 binds reissued OMH 1.1.1 by full revision and digests in
`content/omh.lock.json`; application and content versions are independent.
The reissue replaces v1.1.1's original source/assets with revision
`74f6145b77041bd50654bbe3e53a7900399a5c68`, under explicit user authorization.
Its lock and archive are verified together; old v1.1.1 locks retain their old
digests and need an explicit reviewed update. Existing caches, receipts and
installations keep their identities until the normal plan/apply workflow.
The prior v1.1.0 binding passed clean-fetch validation before merging (PR #7/#8;
CI runs 40519377781, 40624948561 and main run 40627262161).
OMH 1.0.0 is the historical pre-Hub baseline with the old installer and Watcher
automatic collection hooks. OMH 1.1.0 publishes content only: no distribution
CLI and no maintained hooks. Auditing and validation scripts belong to their
consuming skills. Reissued 1.1.1 adds OMH standalone distribution and the shared
Python runtime provider; ATM keeps Rust distribution and its own receipts.
Historical report support and skill-maintainer are removed.
Use the existing `mattpocock-skills:writing-for-agents` for agent-guidance authoring. Third-party
shell distribution outside OMH standalone is the user's responsibility; it does not change ATM's
ownership policy or authorize edits to an existing installation.

ATM’s command-line distributor is its existing Rust CLI. OMH also offers a standalone Python distributor for independently owned targets; see [ADR 0031](adr/0031-omh-owned-runtime-and-independent-distribution.md). Build it
without the desktop crate, frontend tooling or GUI libraries:

```sh
cargo build --locked --release -p atm-cli
python scripts/Prepare-Content.py --cli target/release/atm
python scripts/Package-Release.py --cli-only --output artifacts/atm-cli-local
python scripts/Test-Distribution.py --cli-only artifacts/atm-cli-local.tar.gz
```

On Windows use `target/release/atm.exe` and the generated `.zip` archive.
Python in these commands is build/test tooling; the extracted `atm` executable
performs static distribution without it. CLI and desktop use the same service,
`ATM_HOME` (default `~/.atm`), receipts, locks and recovery journals. There is no
OMH-specific second owner. Python payload runtimes remain explicitly selected.

A withdrawn or unpublished release is unavailable to a clean network fetch.
Before publication, export the exact committed OMH source with its pinned ATM
exporter and import that archive with its reviewed lock into a disposable manager.
Copy that verified imported payload into an empty ignored `harness/` for local
package validation. This is local artifact verification, not evidence that the
release URL works. Do not merge a consumer lock before its public assets are
available and the ordinary clean-fetch CI has passed.

Changing the source lock does not migrate an existing Home. A Home that
installed content under the superseded 1.2.0-bound lock keeps those content
identities, receipts, caches, venvs and recovery archives; moving it to the
pinned release remains an explicit preview/apply. Do not relabel records.

```sh
atm harness bootstrap
atm harness plan install --harness claude-code,codex
atm install skills --harness claude-code,codex
atm check skills --harness claude-code,codex --strict
atm harness status
atm harness -- doctor
```

`bootstrap --source /absolute/payload` and `sync --source /absolute/payload` select
a verified source. Neither applies client files nor invokes Python. `update skills
--harness ...` reconciles selected targets and refuses edited or foreign files.
`uninstall skills --harness ...` removes only recorded ownership. Local skill
commands without `--harness` continue to protect distribution-owned resources.

To import a reviewed lock use `harness import --lock /absolute/omh.lock.json`, with
`--archive /absolute/omh.omh` for a local artifact. Import creates only inactive
cache. The content contract is in [OMH_CONTENT_CONTRACT.md](OMH_CONTENT_CONTRACT.md).
Python helper groups require explicit `harness runtime prepare <group> --python
/absolute/interpreter`. ATM calls the verified OMH runtime implementation;
`--deployment-root /absolute/runtime-storage` selects final-path venv storage,
separately from any skill target. `--external-venv /absolute/venv` validates and
reuses an existing OMH or other venv without modification. `--offline` uses
existing hash-locked wheels. No project or
global environment is owned by ATM. Skill-watcher hooks cannot be enabled;
`uninstall hooks --harness codex --dry-run` previews exact receipt-based retirement.
Historical logs and unrelated hooks remain intact.

## Explicit manager-home handoff

First back up the current manager, affected client files and shell references to
an independent private location. `migrate` requires an absent destination, or the
same incomplete reservation from an earlier attempt. It refuses overlap, changed
receipts, target-root drift, edited files, active old hooks and external runtimes.
All currently recorded targets move together; it does not discover new targets.

```sh
atm harness migrate --home /absolute/old-home --to /absolute/new-home \
  --source /absolute/verified/payload --dry-run
atm harness migrate --home /absolute/old-home --to /absolute/new-home \
  --source /absolute/verified/payload --python /absolute/base-python --offline
```

The preview writes nothing. Apply reserves the destination without an active
receipt, caches content and rebuilds exactly the recorded runtime groups at their
final paths. It preserves old environments and copies available offline wheels;
selected dependency hashes are still enforced. Failed preparation leaves inactive
reusable destination state and the original owner intact.

One existing journal at the destination then marks the source retired, reconciles
client references, removes its old active receipt and publishes the new receipt.
The destination `state/relocation.json` retains the original receipt and source
path. `state/relocated.json` blocks further changes through the old manager.
Cross-file visibility is journaled, not claimed to be fully atomic. Ordinary
operations refuse an incomplete destination; recover explicitly with
`atm harness recover --home /absolute/new-home`, which locks both managers and
preserves any post-crash user edits for manual resolution. Do not delete journals.

After successful receipt, repeat-plan and explicit interpreter checks, switch the
proven shell `ATM_HOME` reference to the new path. Archive the old manager outside
its former active location; do not rename its venvs into the new manager or leave
an alias owner behind. A stale shell pointing to the former home is refused using
the canonical `.atm` owner's retained handoff record; start a new login shell.
Keep the independent backup and historical logs. A rollback
requires restoring the consistent backed-up manager/client/shell set; starting an
old binary against new state is not rollback.

Disk distribution, fresh-shell command resolution and helper health are separate
from actual client loading/invocation. Do not enable hooks to test loading.

## Persistent Python bindings and OMH owner handoff

For supporting content, ATM installs `.omh-runtime` beside the harness skill root.
After explicit runtime preparation, a future session runs
`sh /absolute/harness/.omh-runtime/run.sh workflow /absolute/skill/scripts/helper.py ...`
or the adjacent `run.ps1` on Windows. These OMH launchers select the persistent
interpreter, verify the group requirements and preserve argv. An explicit
absolute `OMH_PYTHON` overrides the binding for that invocation; invalid overrides
fail and helper execution never invokes pip. ATM switches bindings and its receipt
in one recovery journal; generated machine paths are absent from author content
and native plugin package bytes.

OMH and ATM share the target owner marker and OS lock. To change products,
uninstall through the current owner, complete any pending recovery, inspect the
target, then install with the other owner. Neither automatically adopts a foreign
marker or an occupied unowned skill slot. Venvs survive skill uninstallation,
including externally reused environments. The new runtime provider/launchers need
the provider-bearing OMH content now pinned by this repository. To check a clean
payload with actual isolated runtime preparation and all four helper consumers:

```sh
python scripts/Test-Distribution.py --payload-only harness --cli target/debug/atm --runtime-smoke
```

The three native CLI package jobs run this explicit smoke against the extracted
published payload. Static distribution is checked first with no Python on PATH;
only the additional smoke supplies a bootstrap interpreter and prepares venvs.

Runtime verification uses actual venv/version/import/dependency checks rather
than old marker formats. Explicit prepare can complete an interrupted OMH-owned
venv at the same final path; it does not rebuild unknown incompatible directories
or modify external venvs. Formatting or annotations in a same-owner target marker
do not block updates. Invalid explicit Python selections still fail directly.
