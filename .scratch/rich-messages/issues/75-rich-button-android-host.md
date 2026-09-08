# Consume native rich-button observations through ordinary Android input

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: frozen contract70; real guest acceptance needs reviewed adapter72

Own this ticket, new `src/gramlab/_android_rich_buttons.py`, scoped observation-launch support
in `src/gramlab/_android.py`, and new `tests/test_android_rich_button_host.py`. No other production,
existing tests, native patches, lockfile or shared documentation edits. Coordinator owns the
registry/World/SDK, merges, compilation and actual guest acceptance.

Implement `AndroidRichInput(android: Android)` under the
[frozen contract](../../../docs/development/rich-button-implementation-contract.md), with these
structural backend methods (do not import the unfinished coordinator registry):

- `observe(record: dict[str, Any]) -> str`: record is exactly chat/message/revision from an
  authorized World snapshot. Set the private activation after any persona data clear and before
  launch, open the selected chat and return the verified actual client process-lifetime nonce.
  An optional launch hook/argument in `_open_chat` may supply these private files; its default
  behavior must preserve all existing callers.
- `prepare(receipt, *, client_nonce) -> dict[str, Any]`: consume the claimed receipt's target and
  operation ID, verify current World/message/revision and original instance/window/geometry,
  retain original evidence before final freshness checks, and arm the exact operation. It must
  not restart the client or dispatch a touch. Return private dispatch context under `context`
  and a conservatively bounded prospective final receipt under `receipt_for_size_check`.
  The coordinator journals/preflights that receipt before recording dispatch intent; the
  prospective value measures size only and never supplies a reported effect.
- `dispatch(receipt, prepared) -> dict[str, Any]`: one ordinary touch, then exact retained
  effect/correlation and authoritative World confirmation. Return exactly status/dispatch/effect/
  reason/evidence updates from the contract; status is succeeded or uncertain. Do not mutate
  the supplied receipt/target, retry input or call `_open_chat`.
- `reconcile(receipt) -> dict[str, Any] | None`: read retained actual effects only; return the same
  outcome shape when conclusive, otherwise None. No input, restart or new arm. A known mismatch
  never becomes success. Finish/disarm one operation without overwriting its retained artifacts.

Use actual process nonce, activation, generation and guest monotonic time, fully visible finite
original bounds and exact semantic target. Validate all fields/shapes/limits across the private
protocol. Available mapping does not imply every target is visible. Wrong PID/nonce, stale
revision/layout, hidden/clipped/unmapped target and oversized/non-text clipboard reject before
touch. Callback confirmation requires exact original-object/request/token/HTTP ID/returned ID
chain plus complete frozen World callback message/payload/revision. Copy and disabled need the
original action/suppression evidence and actual bounded clipboard; metadata/equality alone is
insufficient. Keep original absent disabled UP evidence rather than inventing it.

The existing v4 World snapshot/dependency methods suffice for independent host development at
the assigned base. Do not add or bypass World ownership APIs. Use a real World plus independently
authored private evidence at the external guest boundary for focused host tests. Clearly identify
that substitution and never count it as native acceptance. Cover successful/rejected matching,
stale/lifetime/correlation mismatch, at-most-one input across preparation/reconciliation, malformed
framing and copy/disabled evidence. Preserve meaningful focused red/green and scoped typing/lint.
No guest, full gate, build, external traffic or fake successful native evidence. Coordinate any
discovered adapter protocol deficiency with the coordinator rather than weakening verification.

## Ownership

Claimed by implementation worker `rich-button-android-host` on `task/rich-button-android-host`.
Focused host verification substitutes only external guest evidence; native acceptance is coordinator-owned.

## Implemented worker handoff

The host adapter now consumes strict bounded private schema-1 observations, verifies the actual
process nonce/PID, guest-uptime freshness, focused app and complete canonical mapping, retains
original pre-input captures, rechecks revision/lifetime/geometry and waits for the exact arm
acknowledgement before returning preparation. Dispatch issues one ordinary ADB tap and confirms
only original action evidence plus the complete frozen World callback/revision, or actual bounded
clipboard evidence for copy/disabled. A 250 ms observed World quiet interval accompanies local
effects; this is bounded evidence, not a global quiet guarantee.

Per-operation JSON snapshots remain immutable. Known mismatches cannot become success. Readonly
reconciliation can confirm a retained exact effect after an input reply is lost. Bounded malformed
framing and oversized effect diagnostics are referenced from Android observations. The prospective
receipt reserves worst-case clipboard JSON escaping and artifact path lengths and supplies no
actual reported effect. A failed disarm preserves a known effect, records pending cleanup and
blocks another input rather than replacing an outstanding arm.

### Approved interface clarification

The coordinator approved `abort_prepared(receipt, prepared) -> None`: idempotently disarm only
the exact prepared arm after registry size preflight or intent-journal failure, without input,
restart or changes to retained evidence. Registry cleanup must call it even if journal writing
is poisoned. `reconcile` remains readonly and is not used for abort cleanup.

### Focused evidence

All commands use the assigned checkout's pinned `tools/dev default --offline` environment,
provisioned through a separate virtual environment and local cached locked packages.

- Initial missing-module red: `artifacts/rich-button-host-red.xml`. The first World fixture
  omitted required `skip_entity_detection`; that fixture failure remains separately retained.
- Meaningful behavioral red: `artifacts/rich-button-host-race-red2.xml` shows the first
  implementation falsely succeeding when the process restarted during ordinary input.
  The corrected implementation checks process/lifetime when confirming retained effects;
  `artifacts/rich-button-host-race-green.xml` passes all 37 tests at that stage.
- Final host command: `tools/dev default --offline --command unshare --user --map-root-user --net
  .venv/bin/pytest tests/test_android_rich_button_host.py
  --junitxml=artifacts/rich-button-host-verified.xml -q`: **50 passed**.
- Scoped Ruff lint and format checks pass for `src/gramlab/_android_rich_buttons.py`,
  `src/gramlab/_android.py` and `tests/test_android_rich_button_host.py`.
- `tools/dev default --offline --command .venv/bin/mypy --strict` with those same three paths:
  **no issues in 3 source files**.

Coverage includes exact row/inline callback, copy and disabled effects, frozen callback answers,
lost replies and at-most-one input, clipboard action/equality distinctions, unavailable clipboard,
non-finite/clipped bounds, boolean paths/integers, duplicate labels and offscreen availability,
same-clock/ABA edits after capture, lifetime changes during input, exact callback revision races,
immutable evidence, malformed UTF-8/JSON, asynchronous acknowledgement, abort and disarm failure.

The tests use a **real World with independently authored guest observations and substituted
external guest input/capture boundaries**. They create no invented native PNG and provide no
native acceptance evidence. The GPL observer must supply actual armed clipboard baselines and
original copy/disabled pairs, preserve full mapping availability independently of offscreen
targets, and retain exact request-object correlation. These deficiencies were reported to the
coordinator and observer reviewer. No guest, build, full gate or network execution ran.

Work remains claimed until coordinator review/integration and required native acceptance. Shared
contributor/CI typing scopes, compatibility and handoff updates remain coordinator-owned.

### Coordinator review correction

The reviewed follow-up closes the interval between preparation and the coordinator's durable
intent. Dispatch now rereads the exact arm command and its strict acknowledgement, requires
`armed` with no original DOWN/UP, action or request, preserves a local-effect clipboard baseline,
and calls the current World/lifetime/window/geometry freshness check immediately before marking
the sole ordinary input handoff. A failed check after intent returns `uncertain` with
`dispatch: intent_recorded`, disarms the exact operation, and sends no touch. Repeat dispatch
returns that same result; readonly reconciliation cannot invent an input for this state.

The callback sizing placeholder is now 64 lowercase hexadecimal zeros, preserving its encoded
size while satisfying the actual journal's callback framing contract. Three new checks exercise
`Journal.allocate`, `transition("claim")` and `preflight_receipt` on actual callback/copy/disabled
prospective receipts and verify preflight leaves the durable journal unchanged. These checks used
the guarded temporary dependency receipt `rich-button-host-primitives-01`, source commit
`56dc9880c8c6385904f3c24be644c53f4c80a601`, for the reviewed journal/traversal helpers.
Those helpers are coordinator-owned integration dependencies, not additions to this worker commit.

- `artifacts/rich-button-host-final-check-red.xml`: eight meaningful failures for a World edit,
  stale guest uptime, changed geometry/PID/nonce, changed arm command and consumed/touched arm
  between preparation and dispatch. Each now returns uncertainty without input.
- `artifacts/rich-button-host-journal-red.xml`: the actual journal rejects the original callback
  sizing placeholder; copy and disabled preflight controls pass.
- `artifacts/rich-button-host-review-green.xml`: **61 passed**, using the same isolated focused
  pytest command above with this JUnit output path and the guarded frozen helper loan.
- Scoped strict mypy still passes all three owned Python files; final Ruff lint/format and
  whitespace checks pass. Cleanup/reconciliation preserve one input handoff, exact disarm,
  terminal results and the distinction between retained evidence and a dispatch attempt.

No native, guest, build, full-gate or external-network evidence is added by this correction.

### Final observation and late-completion review correction

Post-input confirmation now passes the accompanying observation through the full strict schema,
activation/lifetime and complete frozen-mapping validator, checks the current app PID/window and
persona/chat, and enforces guest-uptime freshness and monotonic observation generations. Invalid
observations remain diagnostic evidence, never success. This does not compare the current World
message with the old record: an exact authoritative frozen callback can succeed after the bot
has already edited its message, including a valid observation that the activated old revision
is no longer applied.

Native `complete`, `unavailable` and `uncertain` states cannot switch to another terminal state.
An established clipboard pair cannot disappear, its `before` cannot change, and its `after` can
move only from the baseline to the exact selected text with original copy/UP evidence; it cannot
change arbitrarily or reverse. Consumed copy evidence must retain the actual baseline pair, a
requirement coordinated with the GPL observer worker. Callback-only arms use null clipboard
evidence rather than creating a needless clipboard dependency.

**This supersedes the earlier unconditional terminal-observation cleanup description:** an
unresolved dispatched arm remains live after an uncertain host receipt so truly late callback
completion can arrive through the original native correlation guard. Another preparation rejects
while that arm is outstanding. Reconciliation never arms, touches or restarts; it reads actual
evidence and disarms the exact arm only after conclusive success or a known mismatch. A deliberate
new observation may instead record permanent abandonment and disarm the unresolved operation
before its already-authorized cold launch. Old abandoned operations cannot later recover.
Pre-touch failures may still disarm immediately, and already successful receipts stay immutable.

- `artifacts/rich-button-host-late-observation-red.xml`: 13 meaningful failures cover malformed
  and unrelated post-input observations, stale uptime, terminal-state switches, clipboard removal,
  premature disarm and explicit observation abandonment; the legitimate bot-edit control passes.
- `artifacts/rich-button-host-clipboard-progression-red.xml`: the stricter arbitrary-after-value
  control initially fails; baseline-before and original-copy controls pass.
- `artifacts/rich-button-host-late-final.xml`: **79 passed**, including actual callback completion
  after the uncertain receipt, readonly late success followed by disarm, sticky late mismatch,
  explicit abandonment, consumed baseline preservation and all earlier host controls.
- Scoped strict mypy, Ruff lint/format and whitespace checks pass. The final post-test edit only
  annotates the external guest test boundary's result type; behavior remains unchanged.

The full focused suite used the guarded journal/traversal dependency receipt
`rich-button-host-primitives-02` from integrated commit
`70248cdd4b0c98bb37fadb562eede545ea9e9b44`, including the three actual journal preflight tests.
Borrowed helpers remain coordinator-owned and are restored before this worker commit. There is
no guest/build/full-gate/external-network or native-acceptance claim.

## Coordinator integration

The reviewed host passes 101 combined host, current-message, registry, public scenario and
actual interruption checks (two Android cases deselected), retained in
`artifacts/rich-button-host-integrated-01.xml`. Ruff and strict mypy pass the integrated
production package and four focused test/probe files. Actual native acceptance remains pending.
