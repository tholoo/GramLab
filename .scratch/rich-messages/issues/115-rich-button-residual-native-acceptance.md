# Close residual native rich-button acceptance

Type: task
Status: ready-for-agent
Work state: open
Owner: unassigned
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
