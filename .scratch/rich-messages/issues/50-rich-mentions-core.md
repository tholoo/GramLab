# Implement approved explicit mention admission and projection

Type: feature
Status: ready-for-agent
Work state: resolved
Blocked by: none

Own this ticket, `src/gramlab/rich_messages.py`, `src/gramlab/world.py`, `src/gramlab/bot_api.py`,
and new `tests/test_rich_mentions.py`, `tests/test_rich_mentions_api.py`,
`tests/test_rich_mentions_bridge.py`. A bounded change to `src/gramlab/client_bridge.py` is allowed
only if existing route-level error handling needs the documented legacy rejection. Do not edit
shared docs, native patches, media probes, dependency manifests or existing broad test fixtures.

Follow the frozen `docs/development/mentions-implementation-contract.md`, approved proposal and
ADR 0005. Implement the entire core/API/v3 replay and compatibility contract with independently
specified public-boundary tests. No new persistent schema/grant table, external access, profile
navigation, automatic detection, or change to approved fidelity. Keep existing media behavior.

Use behavioral red before production changes. Compare complete public JSON/form responses and
World/history/events/revisions/identifiers across valid/rejected send/edit/no-op and reopen.
Cover bot knowledge and forged claims, signed 64-bit ID boundaries, budget/recursive labels,
message-derived identity disclosure, historical/truncated replay and frozen callback dependencies.
Selected legacy content must reject before effects; unrelated conversations preserve output.
Current profiles are immutable. Surface an actual contract inconsistency to the coordinator
rather than choosing a consequential alternative silently.

Run focused tests under the outer loopback-only guard, Ruff/format and strict mypy for touched
scope. Use this worktree's pinned environment with verified imports. No guest/APK build. Send
frozen clean commit, exact evidence, remaining native requirements and shared-doc updates;
coordinator reviews/merges and runs combined core/native acceptance. Follow parallel-work.md.

## Worker evidence

Implemented recursive `text_mention` validation with transactional bot-knowledge admission,
ID-only World/client persistence, authoritative Bot API User projection and exact message-derived
v3 identity dependencies for snapshots, selected historical changes and frozen callbacks. Legacy
versions reject selected mention content, including an idempotent callback retry after the current
message removed its mention. No schema, navigation, automatic detection or persistent grant was
added.

The pre-change public rich validator rejected a valid mention with
`GRAMLAB_UNSUPPORTED: rich content fields`. The final guarded focused World, JSON/form API and
real HTTP bridge suites pass 20 tests with `ResourceWarning` promoted to an error. They cover
missing, malformed, unknown and other-bot-only identities; rejected-edit state and identifier
invariance; duplicate nested mentions and existing depth/byte budgets; JSON/form send and edit;
`getUpdates`; v1/v2 rejection; and exact v3 snapshot, truncated changes and frozen callback
envelopes. The earlier guarded selected mention, rich, media, World, Bot API and bridge regression
run passed 111 tests before the follow-up added test coverage without changing production. Scoped
Ruff format/check and strict mypy pass for all three owned test modules; scoped production static
checks passed before the test-only follow-up.

Remaining acceptance is the coordinator's combined core gate and native rendering/round-trip
work. The focused suite does not claim an exhaustive combinatorial pass over every rich block
carrier or mutable-profile behavior (profiles are immutable), and automatic `@mention` detection
is outside this ticket. No guest, APK build or full core gate was run here.

A follow-up fixes legacy callback idempotence to evaluate the frozen stored callback before
applying current-message-only compatibility checks: a frozen plain callback still retries through
v1 after its current message gains a mention, while the inverse frozen-mention case still rejects
after removal. The final focused suite passes 24 tests; 10 selected legacy/media callback and
bridge regressions also pass. Expected HTTP replay bodies are spelled independently rather than
copied from World return values. Additional public tests cover recipient mentions, World-local ID
resolution and rollback of a photo allocation preceding a rejected mention. `create_user` assigns
sequential IDs and exposes no requested-ID parameter, so admitting the maximum signed 64-bit ID
cannot be exercised through the public API without an infeasible number of allocations; its
validator boundary remains covered as a rejection immediately above the maximum. Ruff and strict
mypy pass for the touched production and owned test files.


Coordinator integration passes all 496 non-Android tests at 81.98% coverage in 64.12 seconds,
with four isolated workers and verified primary imports. Full Ruff check/format, production mypy
and strict typing for the three mention test modules pass. Cross-World coverage now uses different
authoritative names for the same numeric ID, so it detects accidental foreign profile reuse.
The callback retry fix is integrated: compatibility follows a stored callback's frozen message
before considering current content for new publication. Native codec/rendering/live bot acceptance
remains in tickets 52 and 54; this resolution covers the assigned core/API/bridge contract only.
