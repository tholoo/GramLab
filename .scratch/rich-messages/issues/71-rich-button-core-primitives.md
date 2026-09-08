# Canonical rich-button occurrences and durable operation journal

Type: task
Status: ready-for-agent
Work state: resolved
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
  future record budget. `preflight_allocation(observation, *, user_id, client_nonce) -> None`
  validates the same whole allocation and conservative future-sequence framing without changing
  state, so a dummy bounded nonce can be used before native launch. `transition(kind, receipt, *,
  client_nonce) -> None` accepts only claim,
  intent or receipt and verifies progression. `evidence(operation_id, evidence, *, client_nonce)
  -> None` appends a changed bounded evidence record. `preflight_receipt(receipt, *, client_nonce)
  -> None` validates a prospective final receipt with exact record encoding and a conservative
  maximum future sequence width without writing or advancing state. `close() -> None` releases the
  owned writer.
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

## Answer

Canonical traversal now enumerates detached row and inline button occurrences through every
admitted rich container in the frozen order. The durable journal exclusively creates and fsyncs
its run file, validates exact identities and monotonic operation states, reserves bounded target
capacity, poisons its writer after append failures, preflights prospective receipt framing, and
derives interruption receipts from strictly validated complete JSONL records.

The retained red report `artifacts/ticket71/journal-red.xml` fails collection because the journal
module does not exist. The guarded follow-up report
`artifacts/ticket71/core-primitives-followup.xml` passes all 18 traversal and journal cases. Scoped
Ruff, Ruff format, and strict mypy pass for the four owned implementation/test files. Android,
guest, integration, and full-suite checks remain the coordinator's separate gates.

Coordinator integration review additionally required preflighting an arbitrary prospective
receipt before target allocation. Preflight therefore performs shape and exact conservative
framing checks without live state, then applies identity, terminal, and remaining-reservation
guards whenever the target or operation is known. Recovery admits only integer schema/sequence
fields and reads at most the journal cap plus one byte, independent of mutable file metadata.

The final journal review preserves `intent_recorded` when interruption cannot prove backend
handoff and makes `effect_mismatch` uncertainty irreversible. Evidence now advances monotonically
for the fixed mode, World-event prefix, action-specific clipboard observations, and native
observation/effect/capture paths. Complete callback effects bind the allocated user, target action,
canonical occurrence, and actual frozen World callback message; conservative preflight values
remain structural sizing inputs until transition. Recovery recursively rejects parsed overflow
floats and rejects an incomplete tail over 128 KiB before discarding it. The retained state red is
`artifacts/ticket71/journal-state-red.xml`; final evidence is
`artifacts/ticket71/core-primitives-six-fixes.xml`.

Callback-message review verifies the exact required World fields `id`, `chat_id`, `sender_id`,
`date`, `text` and `rich_message`; only `edit_date` and `reply_markup` may additionally appear.
Identifiers use positive signed-64 integers, timestamps use nonnegative signed-64 integers, rich
text is empty, and edit time cannot precede creation. Ledger validation also recomputes the exact
World/chat `chat_instance`; it does not invent unavailable revision or snapshot proof. Actual World
positive and malformed message evidence is retained in `artifacts/ticket71/callback-message-red.xml`
and `artifacts/ticket71/callback-message-green.xml`.

Allocation preflight shares the actual allocation's candidate-ledger validation, exact encoder,
80 MiB reservation arithmetic and 128 KiB record cap. It neither writes nor reserves targets and
accepts a valid dummy nonce before native observation establishes the process nonce. The final
guarded traversal/journal report is `artifacts/ticket71/core-primitives-final-followup.xml` with 22
passing cases.
