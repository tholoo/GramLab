# Verify real-bot rich buttons through original rendering and live RTL edits

Type: task
Status: ready-for-agent
Work state: resolved
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

## Worker evidence

The independently authored compact scene covers callback, copy and disabled buttons in rows of no
more than two, an inline callback, primary/danger/success/link styles, absent fill alignment and
explicit left/right/center alignment. Dirty mixed-case styles, tabs in labels and copied text are
separate from the canonical expectations. The edited scene is RTL and retains short Persian/English
labels. Ordinary headings and paragraphs provide XML readiness anchors without claiming that rich
row labels are accessible.

The existing real standard-library HTTP fixture bot sends and edits this scene through the Bot API.
The focused loopback-only simulation passes, comparing complete API replies, durable edited history
and the empty pending update queue against the independent canonical scene. The prepared Android
host test reuses the native `probe(scene_checks=...)` seam and requires complete initial/edited
native serialization, applied live edit, cold restart, three original PNG/XML captures, successful
launches, zero accounts, network and emulator-filesystem isolation, APK fingerprint and an HTML
report. It performs no native input and makes no callback, clipboard or disabled-button effect
claim.

Scoped Ruff lint/format and strict mypy pass for all three new Python files. Native execution,
visual inspection and report inspection remain coordinator-owned against the integrated rebuilt
APK. No guest, build, full gate or external network access was used by this worker.


## Integrated native checkpoint

The normal 13-patch APK builds offline in 2 minutes 50 seconds. The codec case passes in
104.79 seconds with complete catalog/metadata, four valid boundaries, 57 exact rejections and
baseline/isolation checks. The independent real-bot simulation passes in 1.23 seconds after
integration. Original native rendering/live RTL edit/cold restart passes in 67.08 seconds with
complete canonical serialization, zero accounts and guest isolation. All three original PNGs were
visually inspected. The serial Android gate stopped after 19 passes on an older catalog expectation, now tracked
in [ticket 20](20-canonical-catalog-regression.md); this ticket remains claimed pending the
failed and unexecuted cases on the same immutable normal APK. No geometry instrumentation
or button input is part of the normal APK/rendering check.

## Combined normal Android acceptance

All 22 failed-or-unexecuted cases pass on continuation in 1,143.57 seconds. Together with the
19 unaffected retained passes, the exact 41-case collected inventory is covered without skips on
the same immutable normal APK. The stopped 19-pass/one-failure run remains retained; this is
resumed gate coverage, not one uninterrupted green run. The comprehensive catalog's correction
is fixture-only, with complete World/native equality and a fast regression. The full core gate
now passes 370 cases in 58.87 seconds at 81.03% coverage. Experimental geometry/input remains a
separate acceptance boundary.
