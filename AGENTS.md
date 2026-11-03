# ATM repository instructions

- `crates/atm-core/src/distribution/` owns import, plans, receipts, OMH runtime protocol calls and recovery; CLI and desktop use that service.
- `policy/harnesses/registry.json` owns local target paths. Supplier content cannot replace it. `policy/distribution/` preserves published schemas.
- `content/omh.lock.json` pins the independently published OMH release. Generate ignored `harness/` through `python scripts/Prepare-Content.py`; never edit or commit generated content as an authoring source.
- OMH owns skill instructions and content tests. ATM CI runs those tests from the locked OMH revision and tests native distribution and portable payloads here. Import never enables hooks; skill-watcher collection is retired.
- Before changing identifiers or persisted contracts, read `docs/agents/internal-identifier-evolution.md`. Current operations are documented in `docs/HARNESS_USAGE.md`; retain historical ADRs and recovery data.
- Add tracked sources to `scripts/source-manifest.json`; artifacts, private configuration, caches and Home backups stay out of Git.

- OMH owns Python venv preparation, validation and helper startup. ATM calls its verified protocol provider with explicit interpreter/deployment paths; static Rust distribution stays Python-free. See ADR 0031 for target ownership and persistent binding.
