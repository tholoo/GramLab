# Integrate public rich-button operations with World and the actual client

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: interfaces frozen70; implementation dependencies71 and72

Coordinator owns World transaction integration, target registry, Scenario/control/runner wiring,
joint verification. Ticket75 owns the separately reviewed Android host implementation. Follow the
[frozen contract](../../../docs/development/rich-button-implementation-contract.md).
Shared primitive and native workers own their assigned files; do not duplicate their implementations.

Read message ownership/content/revision atomically, reserve ordinary/rich interaction capacity at
allocation, consume targets once and persist intent before backend handoff. Reuse a non-nested
callback transaction helper. Virtual clipboard is client-local; native input uses original touch
without restarting the target's client lifetime. Validate exact native observation/correlation
and retain original evidence. Expose durable offline recovery after supervisor interruption.

Use actual World, HTTP and contained public scenarios for regression evidence. Cover exact callback,
copy/disabled, all canonical paths, wrong identity, same-clock/ABA/unrelated edits, repeat/lost replies,
concurrent claims, resource exhaustion and before/after-intent interruption. Integrate74's independent
same-scenario acceptance. Run focused checks then one applicable combined gate after the integrated
batch. Native acceptance, source/build provenance and wider regression remain required. Preserve
all earlier media/custom-emoji evidence and do not represent unexecuted tests as success.

## Coordinator implementation and evidence

Public Scenario/control methods, World revision transactions, shared capacity reservations,
concurrent single-use claims, client-local simulation clipboard and durable runner recovery are
implemented. Independent ticket74 exercises actual contained bot updates and complete receipts.
The host from ticket75 is integrated; original native acceptance remains pending.

- `artifacts/rich-button-public-integration-05.xml`: 20 public/registry/World/interruption cases
  passed, one Android case deselected, 11.32 seconds.
- `artifacts/rich-button-host-integrated-01.xml`: 101 integrated host/current-message/registry/
  public/interruption checks passed, two Android cases deselected, 21.75 seconds. The host cases
  explicitly substitute external guest files; they are not native proof.
- Review exposed unmarked reconciliation exceptions, discarded late evidence, an invalid backend
  process nonce and deeply nested journal corruption escaping the runner. Focused red artifacts
  retain these failures. The final failure/journal/recovery group passes 41 checks in 12.31 seconds
  in `artifacts/rich-button-failure-integration-green-01.xml`, with scoped strict typing and lint.
- Supervisor interruption uses a test-only bootstrap that exits the actual process immediately
  after real fsync at allocation, claim, intent or receipt; it does not replace World or Bot API.
  Complete and deeply nested corrupt records produce visible recovery failure without replay.

Combined core gate, normal25 APK/native acceptance, clipboard paste, wider placement/isolation and
regression gates remain required. See the new public scenario documentation for actual behavior.

The integrated batch passes the complete core gate: 780 tests, 86.71% statement coverage,
99.12 seconds (`artifacts/rich-buttons-core-gate-01.xml`). Full Ruff lint/format passes 448 files;
strict typing passes the production package plus scoped rich-button checks and independent bot/
scenario fixtures. Configuration and links validate across 213 Markdown files, and the pinned
workflow derivation passes offline. Normal25 APK compilation/signature verification also pass;
original native acceptance is now the remaining action gate.
