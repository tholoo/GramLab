# Complete native rich-button state acceptance

Type: task
Status: ready-for-agent
Work state: open
Blocked by: coordinator integration and native execution

Own this ticket, `tests/test_runner_rich_targets.py`, `tests/rich_targets_scenario.py` and
`tests/fixtures/rich_targets_bot.py`. No production, native patch, profile, shared doc or lockfile
changes. Follow ticket74 and the frozen rich-button implementation contract.

The native status-only gate does not establish complete callback snapshots, quiet World state,
ABA rejection or event/history equality. The current unrelated phase adds two visible-chat
messages after observation and can change native geometry; accepting stale geometry would
violate the independent native freshness contract. Do not demand unsafe dispatch or accept an
unexplained union of outcomes to fit retained output.

Keep the existing full simulation scenario and expectations. Add an explicit fixture-only native
visible-effects/ABA variant ending after the stale repeat, before the unrelated-message phase.
The contained real bot and original input remain unchanged in meaning. Independently spell the
complete native expected history, callbacks, answers, receipts/effects, event ordering and quiet
before/after snapshots. Verify all six visible effects, hidden/offscreen rejections, target identity,
private native observation/effect correlation, first-call ABA rejection and immutable repeats.
Share literal canonical message/target fixtures where sound; never derive expected semantic
values from production output. Dynamic identifiers require validated shape and exact cross-binding.

Reuse the existing native entry point so the coordinator can run it against the reviewed normal27
APK. Preserve the old native result artifacts. Demonstrate useful controls rejecting wrong callback
payload/snapshot, operation-owned quiet-state mutation, wrong revision/identity, extra/missing events
and malformed native correlation using retained real results when practical. Label retained-result
checks honestly; worker execution does not establish fresh native acceptance. Run affected contained
simulation and focused host checks, native collection and scoped static checks only. No guest/build/
full gate. Return a frozen branch with terminal resources and complete handoff.

Actual clipboard paste and native unrelated-revision survival remain explicit ticket74 gaps.
The latter needs a selected-chat-preserving control flow plus real native application/draw evidence;
World acknowledgement or fixed sleeps do not establish it. Do not implement a new public API or
weaken freshness in this acceptance task.
