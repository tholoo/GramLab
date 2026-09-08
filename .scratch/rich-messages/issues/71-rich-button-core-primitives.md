# Canonical rich-button occurrences and durable operation journal

Type: task
Status: ready-for-agent
Work state: open
Blocked by: frozen contract70; no production integration dependency

Own this ticket, new `src/gramlab/_rich_buttons.py`, new
`src/gramlab/_rich_button_journal.py`, new `tests/test_rich_button_occurrences.py` and new
`tests/test_rich_button_journal.py`. No World, SDK, runner, native, existing test, lockfile or
shared documentation changes. Coordinator owns integration and the higher-level registry.

Follow the [frozen contract](../../../docs/development/rich-button-implementation-contract.md).
Implement these independent interfaces exactly; report any required change before implementing it:

- `_rich_buttons.occurrences(content: dict[str, Any]) -> list[dict[str, Any]]`: detached canonical
  `path`, complete `button`, `label` entries in the contract's explicit order. Input is already
  admitted canonical rich content. Preserve hidden occurrences, nested arrays/containers, duplicate
  labels/payloads and custom-emoji alternatives. Do not copy Android traversal code or normalize
  a second time. Reject unsupported structures explicitly.
- `_rich_button_journal.Journal(directory: Path, *, run_id: str, world_id: str)`: exclusively
  create the named journal and durable start record. `allocate(observation, *, user_id,
  client_nonce) -> None` validates and atomically journals the complete allocation, reserving its
  future record budget. `transition(kind, receipt, *, client_nonce) -> None` accepts only claim,
  intent or receipt and verifies progression. `evidence(operation_id, evidence, *, client_nonce)
  -> None` appends a changed bounded evidence record. `close() -> None` releases the owned writer.
- `recover_journal(path: Path) -> dict[str, Any]`: validate all complete records and return the
  exact offline recovery report. It neither writes to the source nor restores input capability.
  Coordinator writes the resulting recovery artifact and integrates it with runner diagnostics.

The journal owns format, fsync ordering, identity/state validation, target reservations, record
counts, strict bounds and a poisoned-writer failure state. The higher-level registry owns shared
ordinary/rich input quota, World validation/action transactions and active client state. Journal
validation failures use ValueError; I/O failures remain OSError. No retry after a failed append.
Empty observations allocate no record/slot. Encoded record limits include newline framing.

Acceptance uses actual admitted World content with independent complete occurrence expectations,
plus real journal files and interruption/reopen boundaries. Cover every supported container,
same labels/different paths, alternatives differing/empty, full exact recovery, claim without
intent, intent without confirmation, terminal immutability, changed evidence, unknown IDs,
wrong identities, invalid ordering, duplicate fields, interior corruption, incomplete final line,
capacity and injected fsync/write failure with no continued writer use. Fsync substitution is
only the external failure boundary; do not replace the journal implementation with a fake.

Run focused guarded non-Android tests, scoped Ruff/format/strict mypy and diff checks under this
checkout's tools/dev. Preserve meaningful red/green artifacts. No guest/build/full gate. Return a
clean frozen branch, terminal processes and a structured handoff; keep this ticket claimed until
coordinator integration succeeds.
