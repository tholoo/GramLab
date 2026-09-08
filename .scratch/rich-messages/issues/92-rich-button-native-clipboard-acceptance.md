# Verify original native clipboard effects through actual paste

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Own this ticket and new `tests/probes/rich_native_clipboard_supervisor.py`,
`tests/rich_native_clipboard_plugin.py`, `tests/test_runner_rich_clipboard.py` only.
Do not change production, existing scenario/test files, native patches, profiles, timeout/freshness
contracts, fixture texts, dependencies or shared docs. Read74/88 and the approved targeting proposal.
Coordinator owns guest execution and integration. No guest/build/full gate assigned.

Native15 now accepts88's complete visible/ABA endpoint on normal27. Remaining clipboard evidence
must prove the actual original Android effect, rather than relying on effect receipts or simulated
state. Stage a bounded test-only bootstrap through the real contained supervisor, preserving the
actual bot/scenario and all existing native dispatch. Reuse88's visible/ABA scenario as input;
do not monkeypatch only the outer pytest process, which cannot observe the contained execution.

After each actual confirmed row/inline copy dispatch, paste through the original visible composer
using the existing UIAutomator input helper and Android paste key event. Assert exact copied text,
then clear the composer through ordinary input and verify its empty placeholder. Keep the two
copy paths independently distinguishable. Verify both disabled row and inline actions preserve
the previously established clipboard text through the same actual paste operation. Disabled row
may leave an owned context popup; first dismiss it through a verified ordinary input action and
confirm the expected composer, rather than pasting into an obscured/unrelated view. Never use a
second rich-target tap to inspect the first effect and never write the clipboard directly.

No additional UI/ADB calls may run between target preparation and real dispatch: that consumes
the target's five-second freshness budget. Establish any baseline before original preparation,
or verify an independently empty composer after dispatch. The post-dispatch probe must not mint
replacement targets, renew lifetimes, retry uncertain taps, relax viewport guards or change runtime
timeouts. Preserve original return values and propagated failures. Bound guest calls by the
existing run deadline and retain operation-keyed redacted evidence on failures as well as success.

Assert no bot send/update/callback or message/history mutation comes from paste/clear: compare
complete relevant semantic state around each probe and retain original UI evidence. Continue to
run the independent88 complete endpoint oracle. Add meaningful host controls for containment
staging, exact returned effects, redaction, deadline exhaustion and incorrect/missing composer
state without claiming those controls prove native clipboard behavior. Preserve original red
when native acceptance is first executed; coordinator will run it after reviewing the frozen branch.
Use the existing pinned environment and focused host/static checks only. Return clean frozen tip,
exact reproduction, terminal processes, evidence paths and pending native acceptance.
