# Implement versioned update selection and recovery offsets

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none — pinned reference contract confirmed

The coordinator owns world/Bot API implementation, dedicated tests and shared documentation.
Inspect migration and polling behavior while the reference ticket resolves the exact contract.
Implement persistent update selection and negative offsets only after source confirmation;
verify behavior at the HTTP/world boundary, including malformed requests before side effects.
Keep the full product goal and consumer workflow open; this ticket covers update delivery only.

Implemented persistent selection at future enqueueing and count-based negative offsets applied
once before a wait. Existing queues, client history and durable callbacks remain intact; excluded
events consume no update IDs. Atomic storage migration preserves prior world/capability/outbox
state across concurrent openers. Tests cover malformed values and requests, defaults, encodings,
scope isolation, sparse queues, later selection changes and empty-wait arrival bursts.

The extended real consumer example selects callbacks, retains a visible filtered message and
recovers the same native callback after bot replacement. Final verification: 179 core tests,
82.16% coverage, all 19 Android tests, 47-file strict typing, lint/format, Nix/workflow checks,
offline distributions and privacy/local links passed. Original captures and desktop/mobile
report rendering were inspected. Reproduce with the gates in
[CONTRIBUTING.md](../../../CONTRIBUTING.md); local run IDs, commands, completed handles and
disposable-image cleanup audit are recorded in ignored artifacts/notes. The APK is unchanged.

Remaining compatibility differences are explicit in
[update delivery](../../../docs/development/update-delivery.md). This resolves the bounded ticket,
not the full compatibility catalog, consumer workflow or product goal.
