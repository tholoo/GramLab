# Verify original native clipboard effects through actual paste

Type: task
Status: ready-for-agent
Work state: implemented on `task/rich-button-native-clipboard-acceptance`; coordinator review pending
Blocked by: coordinator integration and actual native clipboard acceptance

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


## Implemented acceptance boundary

The new Android entry point uses88's `execute`/project staging, including its explicit
`native-visible-aba` variant, then runs both unchanged independent88 prefix/complete-endpoint
oracles. Its opt-in pytest fixture stages the original test-only bootstrap into the actual
contained supervisor. Acceptance compares the bootstrap source marker with both reviewed source
and actual staged bytes. The bootstrap wraps only rich dispatch: it calls the original exactly
once, adds no work before dispatch, preserves its exact return value and propagates its original
exception. A failed post-dispatch clipboard probe is retained separately and fails outer acceptance.

Four independently ordered paths require exact confirmed effects: row copy, inline copy, inline
disabled and row disabled. Each probes the original focused, uniquely identified package composer
only after dispatch, requiring its empty `Message` placeholder before keyevent279 paste, the exact
distinct mixed Persian/English text after paste, and the empty placeholder after ordinary end/delete
keys. No clipboard write, composer-send helper, renewed target, retry, speculative focus fallback,
renderer/profile change or extra pre-dispatch guest command is added. Row-disabled popup handling
reuses strict native PID/UID/parent/surface ownership checks, rechecks the exact focus/PID, sends one
ordinary Back only for that owned popup, then requires the original activity and composer.

Each operation retains original XML and PNG at empty/pasted/cleared stages, redacted command
outputs, original receipt outcome, timing, failure phase/class and complete before/after semantic
snapshots. The snapshots use one read-only SQLite transaction and compare World identity,
all message histories/events, complete callbacks/client sends and bot update-generation counters.
Ordinary polling acknowledgements can remove pending queue rows independently; update generation
and the unchanged88 full bot transcript jointly check that paste/clear produces no new bot update,
message or callback. Failure messages are not retained. Existing evidence is never overwritten.

Probe wrapper commands are capped at32, output at1MiB per stdout/stderr, final JSON at4MiB.
This32 limit is not a total ADB-call count: three original PNG captures and the existing popup
ownership helper also issue bounded calls. Every guest operation uses the original run deadline;
there is no timeout extension. Actual composer focus and popup behavior are native evidence still
pending the coordinator's first run. Preserve its original result even if it fails.

## Worker verification

The initial focused test collection failed because the new bootstrap did not yet exist. The final
host run passes14 meaningful controls in `artifacts/ticket92-host-final.xml`: exact unique/focused
composer state, real bootstrap staging, real World mutation/update detection, original dispatch
return identity/order, wrong/uncertain effects, semantic mutation, UI failure/redaction, original
exception propagation, exhausted deadline, correct/incorrect paste/delete sequence, unrelated
foreground rejection and bounded immutable redacted retention. Guest dispatch/XML are explicitly
substituted external evidence in host controls; these are not native results and no PNG is fabricated.

Android-only collection finds exactly the new test below; it was not executed by the worker.
Scoped Ruff lint/format and strict mypy pass for all three owned Python files. The checkout uses
its own offline provisioned pinned environment; imported GramLab resolves to this checkout.
No guest, APK build, full gate, upstream export or production/shared-source edit was performed.
All host subprocesses are terminal. Native clipboard proof remains open until coordinator review
and actual execution; successful host controls do not establish clipboard behavior.

Reproduction in the assigned checkout:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net \
  .venv/bin/pytest -q tests/test_runner_rich_clipboard.py -m "not android" \
  --junitxml=artifacts/ticket92-host-final.xml
tools/dev default --offline --command unshare --user --map-root-user --net \
  .venv/bin/pytest --collect-only -q tests/test_runner_rich_clipboard.py -m android
tools/dev default --offline --command env MYPYPATH=tests .venv/bin/mypy \
  --strict --explicit-package-bases tests/probes/rich_native_clipboard_supervisor.py \
  tests/rich_native_clipboard_plugin.py tests/test_runner_rich_clipboard.py
.venv/bin/ruff check --no-cache tests/probes/rich_native_clipboard_supervisor.py \
  tests/rich_native_clipboard_plugin.py tests/test_runner_rich_clipboard.py
.venv/bin/ruff format --check --no-cache tests/probes/rich_native_clipboard_supervisor.py \
  tests/rich_native_clipboard_plugin.py tests/test_runner_rich_clipboard.py
```

Coordinator native selection, within the existing dedicated Android gate/profile/APK boundary:
`tests/test_runner_rich_clipboard.py::test_public_native_rich_clipboard_paste_clear_and_disabled_preservation`.
Its fixture stages the bootstrap automatically; no ignored plugin or Java/APK change is needed.
Actual operation artifacts live under `headless-android-run/clipboard-probes/OPERATION_ID/`.
