# Isolate shared-thumbnail acceptance and retain document UI failures

Type: task
Status: ready-for-agent
Work state: open
Blocked by: coordinator integration and native execution

Own this ticket, `tests/test_android_custom_emoji_faults.py`,
`tests/probes/android_custom_emoji_faults.py` and focused diagnostic controls in
`tests/test_custom_emoji_fault_server.py` only. No production, native patch, profile, network
policy, timeout, peer/proxy scheduling, asset or shared-document changes. Follow66/87/89.

The third full native fault run stops in 117.16 seconds before any completed document checkpoint
or the shared case: single-404 same-process reopen returns `Status: timeout` / unknown launch
state, then UIAutomator exits zero with `ERROR: null root node returned by UiTestAutomationBridge.`
and produces no XML. The subsequent cat fails. The phase checkpoint survives, but document-phase
failures do not retain the failure-only native trace/cache/logcat already available for shared
failures. Preserve the original red; it neither proves nor disproves the new shared-transfer fix.
Do not turn a missing UI tree or timed-out launch into a passing original observation.

Add a focused Android test entry point running only the shared-thumbnail case, through the same
probe, immutable APK/profile, explicit isolation and exact existing shared-case semantic/cache/
pixel assertions. Keep the complete original four-case test and its existing selector/acceptance.
Factor staging/execution/acceptance where useful; preserve every existing assertion rather than
copying or weakening it. Each focused run needs its own ordinary dedicated runtime and report,
with honest scope and isolation/zero-account checks. Selecting the focused test must not silently
execute all document recovery phases first. This short gate provides evidence about the changed
shared-transfer fixture while the full regression remains required and the reopen red stays open.

Extend existing bounded failure-only diagnostic retention to document phases before native
force-stop. Check all manifest capabilities, reuse the shared eight-second remaining-time boundary,
retain available actual trace/cache/logcat and exact phase/class without messages, and keep normal
successful guest calls unchanged. Do not add retries, sleeps, launch-status bypasses, success
fallbacks or assertions derived from production output. Keep prior shared failure JSON paths and
successful result shape compatible; make any new document diagnostic fields explicit.

Validate that focused/full selectors retain the independently authored complete assertions, that
failed document diagnostics preserve existing evidence, reject secrets and stop before further guest
calls when the budget expires. Reuse the meaningful87 controls; avoid tests mirroring serialization.
Run focused isolated host tests, native collection and scoped lint/format/strict typing only. No guest,
APK build or full gate assigned. Return clean frozen branch and explicit pending native acceptance.
