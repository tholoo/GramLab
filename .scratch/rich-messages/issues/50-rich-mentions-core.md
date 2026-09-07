# Implement approved explicit mention admission and projection

Type: feature
Status: ready-for-agent
Work state: open
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
