# Integrate public rich-button operations with World and the actual client

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: interfaces frozen70; implementation dependencies71 and72

Coordinator owns World transaction integration, target registry, Scenario/control/runner wiring,
Android host orchestration and joint verification. Follow the
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
