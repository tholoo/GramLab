# Foundation map

## Notes

- [Ticket 01](issues/01-validate-android-seam.md) is claimed; research completed so far is in the
  [source investigation](../../docs/development/android-source-feasibility.md) and
  [host capability report](../../docs/development/android-host-feasibility.md).
- Baseline scaffold committed as `bec0ef4`. An `origin` exists but has not been accessed.
- Host KVM access and a disposable isolated local TCP probe worked. No Android runtime is built
  or running, and no real-bot-to-Android milestone evidence exists yet.

## Decisions so far

- Approved direction remains actual Android rendering, independent MIT core and separate client
  licensing, one world authority and three execution modes, synthetic identities and offline runs.
- [Prototype choices](../../docs/development/android-foundation-proposal.md) are proposed only.
  Source pin, runtime, bridge/provenance, persistence and execution boundary await user review.

## Fog

- Exact emulator/image archive revisions and hashes; Google metadata retrieval returned 404.
- NixOS build environment and native dependency compatibility.
- Full startup RPC requirements, controller/cache reconciliation and accessible real tap behavior.
- Guest and process-level negative egress evidence; namespace probe alone does not cover these.
- Rich-message/media/custom-emoji mapping, Persian assets and full rendering profiles.
