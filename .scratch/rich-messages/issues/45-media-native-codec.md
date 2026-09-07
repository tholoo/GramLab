# Verify native photo descriptors and rejected bridge data

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: normal17 APK for coordinator execution

Own new `tests/probes/android_media_codec.py`, `tests/test_android_media_codec.py`, and this ticket.
Author a bounded native codec acceptance suite using the existing BridgeProbe in patch 0017 and
the contained guest pattern in `android_message_codec.py`. Do not modify production, native patch,
other tests or shared docs. Coordinator owns APK/build/guest execution and integration.

Use independently specified version-3 snapshots from the frozen media contract, PNG/JPEG fixtures
and explicit configuration negotiation. Assert complete output for ordinary photos with caption
entities, rich photos with text/credit caption and repeated-asset deduplication, and a non-media
baseline. Verify malformed/missing asset descriptors, unavailable asset IDs, mixed ordinary/rich
content, wrong version, invalid dimensions/digest/size and unknown fields reject explicitly through
the actual native codec. Preserve all native subprocess output, and distinguish structured
rejection from crashes or invalid JSON. Expected semantic output must come from contract/fixtures,
not a copy of the observed implementation output. Report any uncertain oracle to coordinator.

Read AGENTS.md, handoff, TESTING.md, offline safety and parallel workflow. Run only scoped
Ruff/format/mypy and collection with checkout import preflight, no guest or build. Return frozen
clean committed handoff and exact terminal-resource/static-only evidence. Runtime checks and
source/fidelity conclusions remain coordinator-owned.
