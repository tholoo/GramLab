# Consume native rich-button observations through ordinary Android input

Type: task
Status: ready-for-agent
Work state: open
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
