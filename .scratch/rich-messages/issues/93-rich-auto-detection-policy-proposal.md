# Prepare a reviewable offline rich automatic-detection policy

Type: task
Status: ready-for-agent
Work state: implemented on `task/rich-auto-detection-policy-proposal`; coordinator review pending
Blocked by: user consultation before implementation

Own this ticket and new `docs/development/rich-auto-detection-proposal.md` only. No runtime,
implementation, tests, dependencies, ADR changes, source adaptation, guest or new research.
Use the existing pinned evidence in `rich-auto-detection.md` and the coordinator-reviewed read-only
investigation. The operational requirement remains normal omitted/false detection; silently
accepting the flag while doing no detection is invalid.

Prepare a concrete proposed deterministic offline policy, clearly separating primary-source facts
from choices that cannot currently claim Telegram server parity. Cover candidate classes,
Unicode/punctuation/normalization, scanning scope and precedence, code/explicit-node boundaries,
split siblings/styles, all admitted text roles including button labels, omitted=false=true,
canonical send/edit/no-op semantics, atomic expansion limits, persistence/updates and required
original native projection. Show a few input/output examples that make consequences reviewable.

State that this changes the fidelity target and remains unapproved pending user consultation;
retain exact-parity uncertainty and full operational scope. Do not represent Android or ordinary
TDLib scanning as proof of rich server enrichment. Keep alternatives concise: independent
observations versus an explicit local policy versus a separately reviewed reusable scanner.
Recommend one coherent policy and surface the most consequential tradeoffs in plain language.
Link existing source evidence rather than duplicating large extracts. Validate local Markdown
links/diff and return a clean frozen branch. This is a proposal, not permission to implement.

## Worker result

The new proposal separates the limited pinned facts from every selected local rule, covers the
complete candidate and admitted text-role inventory, and makes send/edit/equality/persistence and
original-renderer acceptance reviewable with concrete examples. It records the absence of a pinned
runtime scanner and keeps dependency/source adaptation behind a separate licensing review.

The fidelity policy remains unapproved. No runtime, test, dependency, ADR or implementation file
was changed, and exact Telegram server parity remains unresolved. The repository configuration and
all local links in 239 Markdown files validate with the documented CI check.
