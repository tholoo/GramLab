# Validate the Android offline integration boundary

Type: research
Status: ready-for-agent
Work state: open
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
