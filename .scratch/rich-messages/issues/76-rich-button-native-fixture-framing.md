# Frame the native rich-button acceptance scene at the original resting viewport

Type: task
Status: ready-for-agent
Work state: unclaimed
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
