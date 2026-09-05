# Validate the Android offline integration boundary

Type: research
Status: needs-info
Work state: claimed
Blocked by: none

Read the foundation spec, handoff, safety requirements and upstream findings. Inspect the current
host/runtime capabilities without changing system services. Resolve a candidate pinned Android
revision and identify the complete request/update, identity, media and initialization paths.

## Acceptance

- Record exact source/license/schema/runtime requirements and authoritative provenance.
- Recommend a minimal client patch/bridge boundary that retains actual rendering and callbacks.
- Account for native initialization, uploads/downloads, push, DNS fallback, WebViews and cleanup.
- Propose a reproducible runtime and independent network enforcement; say whether host changes
  are needed, and ask before enabling Waydroid/KVM/services or installing system components.
- Identify an accessible message/button interaction and rich-message rendering candidate.
- Present consequential design choices to the user, including schema licensing and storage/replay
  where the proposed boundary constrains them. Update the spec with approved outcomes.

Completion is a reviewed, actionable feasibility plan with evidence—not an assumed successful
Android adaptation. If prototyping is needed to answer a question, scope it with the user first.

## Comments

Source pointers are in `docs/development/upstream.md`; no Android build has been run for GramLab.

2026-09-05: Claimed on `research/android-offline-seam`. Existing scaffold committed as
`bec0ef4`; inspecting primary source and host capabilities before proposing implementation.

Research now records the [pinned source findings](../../../docs/development/android-source-feasibility.md),
[host probes](../../../docs/development/android-host-feasibility.md), and a
[concrete prototype proposal](../../../docs/development/android-foundation-proposal.md).
KVM API access and disposable network-namespace local TCP/IPv4/IPv6 probes passed on the host.
No Android build, runtime, bot loop or guest isolation test has run. Exact emulator/image package
revisions remain unresolved after public metadata endpoints returned HTTP 404.

Needs user review of the proposed client/runtime, semantic bridge, schema boundary, SQLite
persistence and isolated prototype provisioning. This ticket stays claimed, not resolved: its
acceptance requires a reviewed plan, and build/runtime claims still require actual evidence.

Handoff verification: locked development tools installed from the existing cache without network;
`uv lock --check --offline`, Ruff lint/format, TOML parsing, local links across 36 Markdown files,
documented probe shell syntax and `git diff --check` passed. Independently rechecked the three
source hashes and request/update/startup/locale paths cited in the source report. No Python
implementation exists, so no behavioral pytest/mypy result is claimed. Next action is user review
of the linked proposal, then approved provisioning and the isolated startup/interaction proof.
