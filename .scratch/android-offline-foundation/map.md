# Foundation map

## Notes

- [Ticket 01](issues/01-validate-android-seam.md) is resolved; the reviewed evidence is in the
  [source investigation](../../docs/development/android-source-feasibility.md) and
  [portable host checks](../../docs/development/android-host-feasibility.md).
- Baseline scaffold committed as `bec0ef4`. An `origin` exists but has not been accessed.
- [Ticket 02](issues/02-offline-world-and-safety.md) is claimed. No offline Android app is built
  or running, and no real-bot-to-Android milestone evidence exists yet.

## Decisions so far

- Approved direction remains actual Android rendering, independent MIT core and separate client
  licensing, one world authority and three execution modes, synthetic identities and offline runs.
- The user approved the [prototype choices](../../docs/development/android-foundation-proposal.md):
  source pin, runtime, bridge/provenance, persistence and execution boundary. The development flake
  and direnv setup implement portable preparation; actual runtime proof remains outstanding.

## Fog

- Runtime metadata is [resolved](../../docs/development/android-runtime-provenance.md); complete
  binary acquisition and boot checks before any fidelity claim.
- NixOS build environment and native dependency compatibility.
- Full startup RPC requirements, controller/cache reconciliation and accessible real tap behavior.
- Guest and process-level negative egress evidence; namespace probe alone does not cover these.
- Rich-message/media/custom-emoji mapping, Persian assets and full rendering profiles.
