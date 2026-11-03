# ADR 0031: OMH-owned runtime and independent distribution

Status: accepted for implementation, 2026-11-03. No real installation, content-lock
advance or release publication is part of this change. This supersedes the
runtime implementation ownership in ADR 0028 and the installer exclusivity in the
original OMH transition. Hook retirement and immutable cache contracts remain.

ATM distributes static OMH content in Rust, without Python. OMH also supplies a
small standalone Python distributor for independently managed targets. These are
two installation owners with separate receipts, not two owners for one target.
ATM never invokes the standalone installer.

Python venv preparation, dependency installation, verification and helper startup
have one implementation in the OMH content package:
`plugins/workflow/scripts/omh_runtime.py`, protocol 1. ATM is its process client.
It supplies an absolute bootstrap `--python`, the verified content root, runtime
specification, deployment root, wheel policy and optional existing external venv.
`--deployment-root` selects venv storage, independently of the harness skill root.
The default remains `<ATM_HOME>/runtimes`; the runtime provider creates final
identity paths and reports a prepared reference. External environments are
validated without marker/pip/bytecode writes. No provider call creates OMH global
installed state. The Rust lock parser remains only for inert source validation.

ATM projects OMH's `.omh-runtime` launcher files and group bindings as ordinary
receipt-owned artifacts. It performs this projection without running Python.
Explicit preparation calls OMH first, then uses ATM's existing journal to switch
content, target bindings and receipt together. Failure preserves old references;
unused new or incomplete environments remain for inspection. Helpers resolve the
stable target binding in future sessions; `OMH_PYTHON` is the sole neutral
invocation override and invalid values fail without fallback. Native plugin bytes
and author source never receive machine paths.

Both distributors use target `.omh-owner.json` and the same OS lock file
`.omh-owner.lock`. The marker records owner, manager and physical target. ATM
journals marker acquisition/removal with its target changes and receipt; apply
and recovery hold the target lock. Old ATM installations add the marker only in
an explicit lifecycle operation. Foreign owners, unowned file collisions and conflicting
changes to managed files block takeover. Owner identity is compared by JSON
fields; formatting and unrelated annotations are preserved. Between products, handoff means uninstall through
the current owner, complete recovery, inspect the target, then install through the
new owner. Existing explicit ATM manager-home migration transfers the marker and
rebuilds managed runtimes/bindings at their new final paths.

Persisted version locks, caches, receipts and historical `.atm-runtime.json`
markers are not renamed or relabeled. New managed references may record optional
`deploymentRoot`; old references remain readable. OMH validates the actual interpreter without reading old or new marker formats
on the execution path. Preparation descriptors only support explicit managed retry. Content without the provider is
still statically installable; new runtime preparation reports
`HARNESS_RUNTIME_PROVIDER_REQUIRED` and requires explicit content selection.
No parallel legacy runtime engine remains in ATM. Uninstall never deletes managed
or external environments. External environments must still be resolved before
ATM's manager-home relocation.

The current `content/omh.lock.json` stays on its published release. New OMH and ATM
source are exercised together locally through OMH's
`check_content_export.py --shared-runtime`; advancing cross-repository pins needs
committed, published, verified revisions and is a separate rollout. Archived ADRs,
real Home receipts, private data and historical release identities stay intact.

Validation retains Rust static source/adapter/service/receipt/journal/CLI/package
gates. Bridge tests observe explicit argv and error transport. OMH owns real
Python tests for final-path creation, dependencies, invalid override, external
preservation and persistent startup. Its cross-repository check covers static
installation with empty PATH, real runtime preparation, binding failure, argv,
manager relocation and two-way owner handoff in a disposable Home. Native Windows
launcher/junction execution requires Windows CI; Linux tests alone do not prove it.

## Compatibility simplification follow-up — 2026-11-03

The bridge no longer repeats OMH write-path/spec/environment checks, carries an
unused verify forwarding API or maps the obsolete INCOMPLETE response. Static
lock validation and provider capability checks remain. Known published receipts
without deploymentRoot still use their recorded root for overlap checks. A
receipt without a target marker still takes the shared target lock for removal;
a genuine absent-target remove creates no target directory. Explicit OMH prepare
can resume an owned attempt at its final path, while helper execution only
validates and runs. Timeout errors are preserved rather than rewritten as wheel
cache errors. No compatibility path selects a different explicit interpreter.
