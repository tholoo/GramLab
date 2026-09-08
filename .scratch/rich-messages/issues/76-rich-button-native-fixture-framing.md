# Frame the native rich-button acceptance scene at the original resting viewport

Type: task
Status: ready-for-agent
Work state: implemented on task/rich-button-native-fixture-framing; native verification pending
Blocked by: native coordinator verification after focused fixture checks

Own this ticket, `tests/fixtures/rich_targets_bot.py`, `tests/rich_targets_scenario.py` and
`tests/test_runner_rich_targets.py`. Follow the frozen rich-button contract and parallel workflow.
No production, existing native patches, shared docs, lockfiles or other tests.

The first normal25 screenshot shows original chat startup aligned to the bottom of the long
rich message. The fixture puts its desired row/inline controls above fifteen filler paragraphs,
while the target named offscreen is visibly at the bottom. This cannot establish the intended
visible-action/offscreen-rejection contract without an unimplemented scrolling operation.

Reorder the independently authored scene so original resting chat placement shows the row and
inline callback/copy/disabled controls, while the offscreen target is before the filler paragraphs.
Keep the closed-details target hidden. Preserve duplicate labels/payloads, Persian/English content,
eight canonical targets, three observations/shared slot usage, stale/ABA/unrelated edits, exact
callback snapshots/events and quiet copy/disabled state. Update independently authored canonical
paths and expected full outputs; do not derive expected traversal from production. Do not change
renderer, host scrolling, viewport, fonts, runtime deadlines or public target semantics to satisfy
the test. Keep the real missing behavior failure if the original viewport still disagrees.

Run the focused actual contained simulation scenario and strict typing/lint/format. Retain the
initial original screenshot as red framing evidence; native green remains coordinator-owned.
Do not run a guest, APK build or full gate. Return a clean frozen branch and structured handoff.

## Worker evidence

The independently authored message now places the intended offscreen callback first, followed by
the same fifteen filler paragraphs. The visible row and nested inline callback/copy/disabled
controls and closed details block are last, matching the original bottom-aligned resting viewport
without scrolling. Canonical expectations retain all eight targets and explicitly use blocks 0,
16, 17 and 18. Scenario actions still select the visible row callback for stale/ABA and unrelated
edit checks, preserving three eight-target observations, duplicate payloads, callback ordering and
clipboard sequencing.

The focused real-bot simulation passes under the outer loopback-only namespace; retained JUnit is
`artifacts/rich-button-framing-simulation.xml`. Collection finds both public tests. Scoped Ruff
lint and format checks pass, and strict mypy with the repository's explicit-package-bases
convention reports no issues in the three Python files. The assigned environment was provisioned
from a copied local uv cache with locked offline resolution. No Android guest, APK build or full
gate ran. The original screenshot remains the framing red; native acceptance is coordinator-owned.
