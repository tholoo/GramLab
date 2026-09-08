# Verify original native clipboard effects through actual paste

Type: task
Status: ready-for-agent
Work state: implemented on `task/rich-button-native-clipboard-acceptance`; coordinator review pending
Blocked by: coordinator integration and actual native clipboard acceptance

Own this ticket and new `tests/probes/rich_native_clipboard_supervisor.py`,
`tests/rich_native_clipboard_plugin.py`, `tests/test_runner_rich_clipboard.py`, and
`tests/rich_clipboard_scenario.py` only (coordinator-approved follow-up scope).
Do not change production, existing scenario/test files, native patches, profiles, timeout/freshness
contracts, fixture texts, dependencies or shared docs. Read74/88 and the approved targeting proposal.
Coordinator owns guest execution and integration. No guest/build/full gate assigned.

Native15 now accepts88's complete visible/ABA endpoint on normal27. Remaining clipboard evidence
must prove the actual original Android effect, rather than relying on effect receipts or simulated
state. Stage a bounded test-only bootstrap through the real contained supervisor, preserving the
actual bot and original native dispatch. Use the approved four-phase clipboard scenario below;
the unchanged88 visible/ABA endpoint remains a separate gate. Instrumentation must run inside the
real contained supervisor, not only the outer pytest process.

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
complete relevant semantic state around each probe and retain original UI evidence. Keep the independent88 complete endpoint oracle as its unchanged separate native gate. Add meaningful host controls for containment
staging, exact returned effects, redaction, deadline exhaustion and incorrect/missing composer
state without claiming those controls prove native clipboard behavior. Preserve original red
when native acceptance is first executed; coordinator will run it after reviewing the frozen branch.
Use the existing pinned environment and focused host/static checks only. Return clean frozen tip,
exact reproduction, terminal processes, evidence paths and pending native acceptance.


## Initial acceptance boundary (superseded by the native03 phase arrangement below)

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

Each operation retains XML with redacted values and original PNG at empty/pasted/cleared stages, redacted command
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

Coordinator reviewed frozen707c931 and integrated the assigned scope. Fourteen focused host
controls pass in 2.03 seconds with the native case deselected; lint, formatting and strict typing
pass on the merged checkout. Contributor and CI commands now include the new strict scope.
Evidence: `artifacts/rich-clipboard-integrated-01.xml`. Actual native acceptance is pending.

## Native01 XML redaction follow-up

The coordinator's first actual clipboard run fails in99.35 seconds after both complete88 oracles
pass. Row-copy's empty-capture XML fails parsing before any paste key is issued: applying the
generic text redactor to the serialized XML changes the native boolean attribute
`password="false"` into unquoted `password=[REDACTED]`. The other probes fail ordered validation
because row-copy never completes. Preserve that native01 result and its original artifacts;
it establishes neither successful paste nor a renderer/input defect.

The bounded correction parses the original1MiB-limited XML, applies the existing redactor to
individual attribute/text/tail values, and serializes well-formed XML. Native boolean attributes
retain their actual values; the unchanged composer password/focus/uniqueness/content checks still
apply. The serialized derivative is also bounded and rejects known capabilities remaining in XML
structure before writing. Evidence explicitly labels this representation
`xml_with_redacted_attribute_and_text_values`; it is not byte-identical original XML. Original PNG
capture/redaction, dispatch hooks, source-hash checks, deadlines and ordinary input remain unchanged.

Two new host regressions run through the actual capture/command-retention path with literal
UIAutomator-shaped XML and explicit external screenshot substitution, without creating a PNG.
Both initially reproduce the exact ParseError class in `artifacts/ticket92-xml-red.xml`.
After correction the false flag passes, the true flag still rejects through composer validation,
quoted/escaped attribute content remains intact, and known capabilities in separate attribute,
text and tail values cannot persist. The complete16-control host suite passes in
`artifacts/ticket92-xml-green.xml`; strict typing and scoped Ruff checks pass. No native01 evidence
was rewritten, and no guest/build/full gate ran. Fresh native02 clipboard acceptance remains
coordinator-owned and unproven until actually executed.


## Native02 freshness diagnosis

Native02 proves row-copy's actual exact paste/clear and equal before/after semantic state;
its post-dispatch probe lasts15.109828611 seconds. Later inline callback/copy/disabled and row-disabled
operations reject before dispatch. Their operation directories exist but contain no retained
observation or capture, locating rejection inside the initial `_fresh` call after the first strict
observation parse and directory creation. Initial geometry equality is not checked there because
preparation has not yet stored geometry. The prior row-copy observation/effect are not the failing
samples; static age, recorded availability and transient focus remain distinct hypotheses.
The before/cleared PNGs show the same visible chat layout, which does not prove observer freshness.
Preserve all native02 results. No accepted arrangement or freshness/runtime behavior is changed.

The test-only bootstrap now wraps original `_fresh` once. Successful calls return the original
object directly. On an original exception, it uses that exception's actual traceback and existing
frame locals, then rethrows the same exception. It issues no guest/private-file/World reads,
clock calls, input, sleeps, redraw, target renewal or retries. At bootstrap installation it hashes
the original function's source file for provenance; failure retention adds only bounded host IO.
The existing operation directory receives immutable `fresh-failure.json` even before registration
in `_operations`. It contains the original source hash/file/line, up to16 traceback entries,
existing `sample`/`pid`/`now`, selected arm/target/identity/geometry flags, and explicit missing-field
lists. Full World records and exception messages are omitted. Known secrets are redacted before
publication; over128KiB records omit detailed state/locals with an explicit reason. Existing
failure files are never overwritten, and diagnostic errors do not replace the original failure.

Four focused controls prove exact return identity, original exception/frame/source/line identity,
missing-local reporting, oversized-detail omission, redaction and immutable repeated evidence.
They initially fail because the diagnostic hook is absent (`artifacts/ticket92-fresh-diagnostic-red.xml`).
All20 host controls now pass in `artifacts/ticket92-fresh-diagnostic-green.xml`; scoped Ruff/format
and strict typing pass. No native02 files changed and no guest/build/full gate ran. Coordinator
native03 retains identical clipboard/input/freshness behavior and must establish the actual failing
sample/guard before any further acceptance arrangement is proposed or changed.


## Approved native03 four-phase follow-up (implemented; native acceptance pending)

Native03 retained actual successful row-copy, inline-copy and inline-disabled paste/clear probes.
Its original failing `_fresh` frame establishes the unchanged five-second draw-age guard: hidden,
offscreen and row-disabled samples age9745/10016/10236ms, before input. All previous native01/02/03
artifacts remain retained failures; this evidence authorizes an acceptance arrangement change,
not a runtime/freshness correction.

The dedicated clipboard scenario now owns four predetermined public observations in the same
World/guest, each beginning a new original client lifetime: row copy; inline copy; inline copy
baseline then inline disabled; row copy baseline then row disabled. Exactly six ordered dispatches
produce four terminal paste/clear probes. Baseline copies in disabled phases have no intermediate
probe. Both actions in each disabled phase use targets from that phase's single observation.
Any rejected/uncertain action fails immediately; no replacement target, retry or guard/timeout
change is permitted. Row-disabled preserves ROW text; inline-disabled preserves INLINE text.

A new independent oracle checks all observations/lifetimes/targets, six exact effects and native
input/provenance, unchanged semantic state around baseline/disabled/probe, and the complete
publication/finish bot transcript with no callback/client-send side effects. Only legitimate empty
polls may vary. The unchanged88 visible/ABA full endpoint remains a separate existing native gate;
this dedicated clipboard scenario does not repeat callbacks, hidden/offscreen checks or ABA.
The original fixture bot and shared88 files remain unchanged. Existing passive freshness diagnosis
and reviewed bootstrap-source equality remain in place. Worker checks are focused host/contained
simulation and scoped static only; coordinator owns fresh native acceptance.


### Four-phase implementation and verification

The dedicated scenario stages through88's unchanged project helper, replacing only its temporary
scenario copy and selecting an explicit `clipboard-four-phases` manifest value. Reviewed scenario,
variant and unchanged bot source hashes must exactly match the actual run report. The bootstrap
and its reviewed/staged SHA equality remain independently checked.

The test-only observer wrapper calls each authorized original observation exactly once, records
its returned client nonce and captures one read-only full semantic baseline afterward. It rejects
an early/new phase after an unfinished or failed phase, a repeated client lifetime, or a fifth
observation. Original observation exceptions propagate unchanged and cannot trigger a retry.
The dispatch wrapper still calls original dispatch before any added work; afterward it requires
the exact next path/effect and matching phase client nonce. It compares the saved full semantic
baseline with the actual post-action snapshot. After each terminal probe it compares another full
snapshot. Six immutable operation directories retain action records; only four terminal directories
contain paste/clear XML/PNG and guest commands. Baseline directories contain `result.json` alone.
A failed post-action check does not change the original dispatch return, but blocks the next phase
and fails outer acceptance. Original dispatch exceptions still propagate unchanged.

The independent endpoint oracle requires32 distinct target IDs across four observations, six unique
operation IDs and exact copy/disabled effects, and unchanged complete canonical state around every
observation/action. Native checks reuse the independently authored88 observation/effect/touch/PNG
validator and require four distinct activation/client nonces with consistent same-phase identity
and the actual retained World ID. Each action record is cross-bound to its receipt and client
nonce. Terminal probes require exact ordinary paste/end/delete input (and at most one existing
owned-popup Back for row-disabled), exact composer XML/text and original320x640 PNG evidence.
The sole bot traffic is initial publication delivery, two exact ordered rich-message responses,
zero or more empty offset2/timeout10 polls, the exact finish delivery, and the final offset3 poll.
Callbacks/client sends remain empty and the generated-update counter is exactly3 at completion.
No fixture/API/World/runtime/native/profile/freshness/timeout behavior changed.

Four new phase controls initially fail against the preceding wrapper in
`artifacts/ticket92-phases-red.xml`. The final focused suite passes26 tests in
`artifacts/ticket92-phases-green.xml`: the prior20 controls, four phase progression/effect/state
controls, original-observation exception/no-retry control, and one real contained simulation of
the complete new scenario. That contained result also supplies nine independent mutation checks
for reused targets, extra actions, wrong copy/disabled baselines, history mutation and invalid
BotAPI poll/write/delivery ordering. These mutations are explicitly simulation controls; no native
recording or PNG is fabricated. The simulation proves semantics only.

Final strict mypy, Ruff lint/format and diff checks pass; Android-only collection finds one selected
clipboard test, without executing it. Add `tests/rich_clipboard_scenario.py` to the four-file scoped
static commands above and select `artifacts/ticket92-phases-green.xml` for focused host reproduction.
All worker subprocesses are terminal. No guest/build/full gate, provisioning, upstream export or
shared-file edit ran. Original native01/02/03 evidence remains untouched. The coordinator must run
fresh four-phase native acceptance; native03 is retained as a failed earlier arrangement and
cannot be relabeled a pass. The unchanged88 full native15 endpoint remains separate evidence.


## Native04 preparation diagnostic follow-up (implemented; native05 diagnosis pending)

Native04's first phase proves row-copy actual paste/clear. Phase2 rejects inline-copy before intent.
The failed operation retains a valid available generation5 observation with a distinct client
nonce/PID and320x640 original before PNG, but no effect or freshness-failure diagnostic. The exact
pending private sample and exception remain unknown. An ordinary `_ready` rejection follows effect
retention, so absent effect evidence instead prioritizes missing/old arm-ACK timeout, guest
read/write failure, or an effect schema rejection before retention; these are hypotheses only.

The coordinator authorizes extending the existing passive traceback diagnostic to original
`prepare`, through a shared helper. Retain only actual existing frame locals/sample/pending/effect
and selected state, source hash/lines, explicit missing fields, bounded redaction and immutable
operation-keyed publication. Preserve exact original returns and exceptions. Add no guest calls,
private-file/World reads, clock calls, timeout/guard changes, input, retry or scenario rearrangement.
Original native04 and all prior evidence remain unchanged. Native05 is coordinator-owned.


The shared failure-retention helper now serves `_fresh` and `prepare`. It locates the original
function's actual traceback frame, retains up to16 original/nested source locations and hashes
original source once per distinct file at installation. Prepare retains existing `sample`,
`pending`, `effect`, and selected state including any existing candidate/effect/baseline. Missing
locals are explicit; a failure before original operation state exists produces no invented record.
Values reflect the actual exception frame after original cleanup. The helper never reads guest
files, World or clocks. Each immutable record is capped at128KiB; oversized details are explicitly
omitted. An operation may retain both `fresh-failure.json` and `prepare-failure.json` (at most256KiB
combined). Diagnostic failure never replaces the original exception. Success returns the exact
original object without diagnostic work.

The new four-mode host control passes the original return directly and initially reproduces three
missing prepare diagnostics (`artifacts/ticket92-prepare-red.xml`). After the correction all30
focused tests pass in `artifacts/ticket92-prepare-green.xml`, including the existing contained
four-phase simulation. Controls verify actual source/frame/line and pending values, missing and
oversized values, secret redaction, immutable evidence and exact propagated exception identity.
Scoped strict typing, Ruff lint/format and diff checks pass. No phase/input/timeout/guard/APK/profile
change occurred, and no native04 artifact was edited. All worker subprocesses are terminal; no
guest/build/full gate or provisioning ran. Root must execute native05 to establish the cause.


## Coordinator native05 diagnosis

The prepare diagnostic is integrated with30 focused checks passing. Fresh normal27 native05 fails
in103.40 seconds after row-copy paste/clear. The exact original prepare traceback now identifies
the arm-acknowledgement wait: the new lifetime's observation matches its new activation/arm, while
the pending effect remains the prior lifetime's completed row-copy operation. Source hashes match
the staged production implementation. No new input was dispatched for the rejected operation.

Source review establishes a retained old disarm is processed before the new arm. Same-persona
cold launch preserves app data; the successful prior operation writes that disarm. Native polling
rejects its old activation/client nonce and swallows the exception before reading the new arm.
The private disarm bytes themselves were not captured in this run; retention follows from the
verified host success/disarm/launch flow. [Ticket98](98-native-disarm-lifetime-scope.md) implements
the operation-scoped correction and independent native regression. No timeout, drawing, input or
freshness change is justified. Native04 guest disks are retired; all failed results, screenshots
and operation diagnostics remain. Full four-phase native acceptance remains pending the fix.

## Claimed native06 popup-settling follow-up

Coordinator authorizes only this ticket, the existing bootstrap and its host/native acceptance
file. Native06 on normal28 completes all six rich actions and the first three terminal clipboard
probes. The final row-disabled action is complete with unchanged ROW clipboard and World state,
but its post-dispatch probe sees the exact owned popup immediately after one Back and rejects
before paste. Eventual dismissal is not established by that run. Preserve native06 and earlier
artifacts. Initial ownership/PID/focus validation stays unchanged; after the single Back, observe
only the same popup until original LaunchActivity regains focus, rejecting changed PID or
unrelated/ambiguous focus. Polling consumes the existing run deadline and32 wrapper-command bound;
no timeout extension, extra input, redraw or target renewal is authorized. Record Back issuance
separately, and only record popup dismissal after the postcondition is verified. Fresh native07
and the final actual paste/clear remain coordinator-owned acceptance.

The implemented loop retains the initial strict ownership and two PID/focus observations, then
issues exactly one Back and records `popup_back_issued`. Each later observation allows only the
same window identity or same-user original LaunchActivity; both require the original PID. A
changed/different/ambiguous foreground rejects immediately. Same-popup persistence consumes the
existing32-command allowance and original run deadline, without any new deadline, sleep, input or
state modification. `popup_dismissed` is set only after verified chat focus. All subsequent original
composer XML, actual paste/end/delete/clear, source-hash and World-state checks remain required.
Native acceptance now verifies both bookkeeping fields whenever the single Back was issued.

The native06 result (SHA256
`bc0ad7a495e9e160254cd81668c5ebc6b44ddb92f901cf9d665f1b5f13ed9b69`)
supplies the exact six-command focus/PID projection for a portable host regression. It is explicitly
limited to retained observations; a scheduled later popup-to-chat transition is an independently
authored external control, not fabricated future native evidence. Initial ownership and screenshot
collaborators are explicitly substituted in these host controls; no PNG or native success is made.
Ten new cases cover that prefix without paste on deadline, immediate/delayed chat return, persistent
popup, partially consumed command allowance, exhausted deadline, changed PID despite apparent
chat focus, unrelated/ambiguous focus and a different popup. Every failure forbids capture/paste;
every case permits exactly one Back, and failure evidence never claims verified dismissal.

All ten controls initially fail in `artifacts/ticket92-popup-red.xml`. After correction the full
40-test host suite passes in `artifacts/ticket92-popup-green.xml`; strengthened wrong-PID and
immediate unrelated-window rejection assertions also pass all40 in
`artifacts/ticket92-popup-final.xml`. The existing contained four-phase simulation remains part
of that run. Strict mypy and Ruff lint/format pass for the four existing probe/plugin/scenario/test
files. No tracked files outside the three authorized follow-up paths changed, and no guest,
build, network, full gate or provisioning ran. Existing native06 files remain unchanged. All
worker commands/contained processes are terminal; fresh native07 on unchanged normal28 remains
required for actual final row-disabled paste/clear acceptance.

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -q tests/test_runner_rich_clipboard.py -m "not android" --junitxml=artifacts/ticket92-popup-final.xml'
tools/dev default --offline --command env MYPYPATH=tests .venv/bin/mypy \
  --strict --explicit-package-bases tests/probes/rich_native_clipboard_supervisor.py \
  tests/rich_native_clipboard_plugin.py tests/rich_clipboard_scenario.py tests/test_runner_rich_clipboard.py
.venv/bin/ruff check --no-cache tests/probes/rich_native_clipboard_supervisor.py \
  tests/rich_native_clipboard_plugin.py tests/rich_clipboard_scenario.py tests/test_runner_rich_clipboard.py
.venv/bin/ruff format --check --no-cache tests/probes/rich_native_clipboard_supervisor.py \
  tests/rich_native_clipboard_plugin.py tests/rich_clipboard_scenario.py tests/test_runner_rich_clipboard.py
```

## Coordinator native07 acceptance

The popup follow-up is integrated after preserving both native05 diagnosis and native06 follow-up
in the ticket merge. All40 focused checks, strict typing and Ruff pass. Fresh unchanged normal28
native07 passes in155.89 seconds: all six action/baseline records and all four terminal paste/clear
probes pass, including row-disabled with exactly one Back and verified return to the original chat.
Full unchanged semantic-state, complete final history/event/API ordering, receipt/effect/source
provenance and isolation assertions pass. All four original pasted and four cleared images were
visually inspected; the retained XML independently proves exact text and empty composer states.
The completed native07 and diagnosed native06 guest disks are retired, with304 other evidence files
verified unchanged. The applicable combined core gate remains pending before resolving this ticket.
