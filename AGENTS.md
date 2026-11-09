# ATM repository instructions

- `crates/atm-core/src/application/` owns configuration preview/apply, templates and quota orchestration; CLI has been retired with ADR 0032 and the desktop app is the only frontend.
- Skills/harness distribution is owned by OMH standalone; ATM ships no distribution code, content lock or target policy. Handover follows the single-owner protocol in ADR 0031 (see ADR 0032 for the exit decision).
- Before changing identifiers or persisted contracts, read `docs/agents/internal-identifier-evolution.md`. Current operations are documented in `docs/HARNESS_USAGE.md`; retain historical ADRs and recovery data.
- Add tracked sources to `scripts/source-manifest.json`; artifacts, private configuration, caches and Home backups stay out of Git.
