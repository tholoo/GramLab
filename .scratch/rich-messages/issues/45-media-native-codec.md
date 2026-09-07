# Verify native photo descriptors and rejected bridge data

Type: feature
Status: ready-for-agent
Work state: claimed
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

## Worker evidence

The bounded app-process probe and 28-case oracle are authored on `task/media-native-codec`:
four accepted snapshots cover non-media baseline, ordinary PNG with caption entity, repeated rich
JPEG with text/credit caption and mixed ordinary/rich messages; 24 rejected snapshots cover every
missing descriptor field, extra fields, unsupported MIME, size/dimension/digest bounds, ordering,
duplicates, missing/unknown message asset IDs and version-2 media. Expected native photo descriptors
retain positive asset/volume IDs and local ID 1 through serialization as required by the frozen
contract. Each subprocess record is preserved. Invalid JSON/crashes are represented separately by
the probe and cannot satisfy the structured exit-2 rejection oracle.

Scoped Ruff format/check, mypy and pytest collection pass with the assigned checkout import. This
is static authoring evidence only. The worker did not build an APK or start a guest. Coordinator
execution against normal17 is expected to expose the already observed upstream PhotoSize
serialization mismatch; the oracle deliberately does not accept negative reconstructed locations.
Snapshot construction deep-copies messages and assets so malformed-case mutations cannot alter the
valid rich inputs or expected output. Two independent inventory constructions retain rich asset IDs
`[2, 2]` and compare identically.
