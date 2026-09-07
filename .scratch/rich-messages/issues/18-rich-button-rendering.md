# Verify real-bot rich buttons through original rendering and live RTL edits

Type: task
Status: ready-for-agent
Work state: open
Blocked by: ticket 15 rebuilt APK for native execution

Use the integrated [button contract](../../../docs/development/rich-buttons-contract.md) and existing
real-bot rich send/edit/restart helpers. Own new tests/test_rich_action_round_trip.py,
tests/test_android_rich_actions.py, tests/probes/android_rich_actions.py and this ticket. The
coordinator owns shared probes, source/APK, integration and all guest execution. Use a separate
worktree. No new public targeting or input contract is assigned.

Author a compact initial and RTL edited scene with independent input and canonical expectations,
covering callback/copy/disabled rows, an inline callback, all four nondefault styles, absent fill
and explicit alignment. Use short bilingual labels and rows with at most two buttons so the current
320x640 profile can expose the relevant original appearance. Keep at least one ordinary visible
heading/paragraph anchor for UIAutomator checks; rich rows lack per-button accessibility. Do not
assert an inaccessible label appears in XML merely because it is present in the world.

Reuse stage_rich_scenario, the real standard-library HTTP fixture bot, rich_round_trip, and the
native probe(scene_checks=...) seam. Compare complete real bot replies, durable history and actual
native serialized initial/edit records. The focused native host test must retain original three
PNG/XML captures, successful launches, applied live edit, cold restart, zero accounts, network and
emulator filesystem isolation, APK fingerprint, complete scene expectations and an HTML report.
No synthetic input occurs in this rendering check; callbacks/copy/disabled action effects belong
to the separate geometry/input experiment. Do not claim native input from rendering evidence.

Run focused real-bot simulation and scoped Ruff/format/mypy under the pinned shell/outer network
guard. Existing codec red already establishes old APK rejection; do not repeat a guest or rebuild.
Positive native execution and visual inspection are coordinator-owned after APK integration.
Commit only owned files; send frozen clean tip and exact checks, remaining acceptance and terminal
resource state. Ticket stays claimed until coordinator integration and acceptance.
