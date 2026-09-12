# Close residual native rich-button acceptance

Type: task
Status: ready-for-agent
Work state: claimed
Owner: task/rich-button-residual
Blocked by: none

The public rich-target API and its callback/copy/disabled actions are implemented. Native15 proves
six visible row/inline actions, nested identity, hidden/offscreen rejection, ABA staleness and exact
callback/World/API correlation; native07 proves actual copy/disabled paste and native03 proves an
unrelated same-layout edit preserves a target. The frozen implementation contract still lacks an
actual truly RTL input case, partially clipped rejection, process-restart invalidation/recovery and
native lost-reply reconciliation. Close only those residual acceptance gaps.

Own this ticket and new files:

- `tests/fixtures/rich_button_residual_bot.py`;
- `tests/rich_button_residual_scenario.py`;
- `tests/probes/rich_button_residual_supervisor.py`; and
- `tests/test_runner_rich_button_residual.py`.

Do not change production modules, Android patches, existing fixtures/tests, shared docs, profiles,
timeouts or dependencies. Reuse the frozen public operations and original observer/input paths.
Request any additional ownership before editing it.

Use one compact contained scenario. Make the visible row start with Persian and use an independently
distinct nested inline control so original layout direction is genuinely RTL. Exercise one callback
and one copy/disabled path through original input, preserving exact callbacks, clipboard and quiet
World state. Position another real rendered target so its measured rectangle is partially clipped;
require exact `clipped` rejection with no touch, request, clipboard or World effect. Observe an
unconsumed target, restart the actual application process, require its old ID to reject with
`client_restarted`, then make a fresh observation and complete exactly one action. Finally, drop one
post-dispatch control reply in the test-only supervisor after the original confirmed effect, repeat
the known target ID deliberately, and recover the same terminal receipt with exactly one original
touch/action and no replay.

Independently spell expected canonical paths/messages, histories, events, callbacks, receipts and
bot transcript. Bind native evidence to exact process/lifetime/revision/geometry/request identity,
one real RTL screenshot, the clipped rectangle, restart PIDs/nonces and retained lost-reply effect.
Keep zero accounts, loopback-only transport, component filesystem isolation and capability
redaction. No automatic scroll, disclosure, long press, new action type or renderer change belongs
to this ticket.

The worker runs a meaningful failing host/contract baseline, contained simulation and focused host
checks, Android collection, scoped strict mypy and Ruff only. No guest, APK build or broad gate.
Coordinator first reruns the existing public rich-target Android case on immutable normal30, then
runs this one focused residual case under `android-gate`; defer the complete Android inventory until
album integration.

## Worker preparation

`task/rich-button-residual` owns this ticket and added one compact, independently specified
real-bot fixture/scenario plus a test-only native supervisor. The source oracle fixes four canonical
paths: the mid-message clipped row control, Persian-first visible row callback/copy controls and a
distinct nested inline callback. The supervisor only wraps the frozen public/original seams: it
records original observations and touches, force-stops/relaunches the actual application once
before old-copy preparation, and drops exactly one already-completed `lost:reply` control response.
It never scrolls, supplies coordinates, invokes an action directly or retries input.

The meaningful red baselines were retained outside Git as
`artifacts/rich-button-residual-red-01.xml` (contained scenario/fixture absent) and
`artifacts/rich-button-residual-host-red-01.xml` (native supervisor absent). The resulting focused
contained gate passes **4/4** non-Android tests in the loopback-only namespace at
`artifacts/rich-button-residual-focused-final-03.xml`. It covers the exact simulation messages,
canonical target order, receipts, histories, events and Bot API exchange, plus single-drop/normal-
repeat host behavior and bounded capability-redacted supervisor evidence. Scoped strict mypy and
Ruff check/format pass for all four new Python files.
Exactly one Android case collects; no guest or APK build was run by this worker, so original clipped
geometry, process PIDs/nonces, RTL capture and lost-reply native correlation remain deliberately
unclaimed until the coordinator's serialized normal30 gate. Keep this ticket claimed until that
integration evidence passes.
