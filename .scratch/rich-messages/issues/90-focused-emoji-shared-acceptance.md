# Isolate shared-thumbnail acceptance and retain document UI failures

Type: task
Status: resolved
Work state: integrated; required native acceptance passed
Blocked by: none

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

## Implemented boundary and focused evidence

The original Android test still stages and executes all three document-fault cases followed by the
shared-thumbnail case with its existing schedules, timeouts and assertions. A separate Android test
stages only the shared world and selects the shared probe path. Both paths reuse the same isolation,
zero-account, cache, trace, pixel and report checks; the focused selector rejects any document cases
rather than silently executing them.

Document failures now record the exact active phase and exception class plus available peer,
document and asset journals. Before the outer cleanup force-stop, they use the existing bounded
eight-second diagnostic path to retain available trace, cache and logcat evidence. Every retained
artifact is checked against every manifest capability, and an expired budget issues no further guest
command. The successful result shape and successful guest call sequence remain unchanged; the
failure checkpoint adds an explicit nullable `document` member while preserving `shared`.

The isolated focused host run in `artifacts/ticket90-worker/focused-host.xml` passes 13 checks. Android
collection exposes four tests, including the new shared-only entry point. Scoped Ruff lint/format and
strict mypy pass for all owned Python files. No Android guest or APK build ran; original native shared
transfer acceptance and the unchanged full regression remain coordinator-owned.

Coordinator integration: reviewed frozen worker commit and independent assertion-preservation
review. All 41 original assertions remain identical; focused shared execution preserves isolation,
zero-account, cache, trace, pixel and report acceptance. Integrated focused checks pass 13 tests
with two native tests deselected; scoped lint/format and strict typing pass. Fresh focused native
execution and the complete original native regression remain required.

Fresh focused normal24 Android acceptance passes in 66.59 seconds, including the original
shared-case assertions, isolation, zero accounts and report generation. The original complete
capture was inspected and disposable successful guest disks retired. Evidence:
`artifacts/custom-emoji-shared-native-01.xml`. The original full fault regression remains required
under66, with earlier failures preserved.
