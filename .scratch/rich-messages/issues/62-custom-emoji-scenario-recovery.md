# Prove custom-emoji registration through scenario control and containment

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: none after scenario registration integration

Own this ticket, `tests/test_custom_emoji_scenario.py`, and new
`tests/test_runner_custom_emoji_registration.py`. Production changes, native code, fixtures,
shared docs and dependencies remain coordinator-owned. Report a concrete defect before widening
ownership. Follow TESTING.md and the frozen custom-emoji implementation contract.

Extend actual authenticated HTTP coverage for wrong capability/world, duplicate JSON/framing,
route-operation mismatch, the registration 1 MiB encoded limit, decoded 512/128 KiB limits and
the unchanged 65536-byte ordinary route. Demonstrate a real dropped response after committed
registration: SDK reports an uncertain write, same request ID recovers the exact descriptor after
reopen, conflict rejects and the next allocated ID has not advanced through duplicate attempts.
Use a local controlled HTTP forwarding peer, not a patched World or pretend decoder.

Exercise a real contained public runner scenario using Scenario.from_environment and the original
static/animated fixtures, allocated and caller-selected IDs, optional flags, persistence and exact
independent descriptor expectations. Confirm the trusted supervisor can actually decode WebM while
bot/scenario components cannot access the decoder executable. Reuse the established runtime fixture
and provisioning; do not weaken containment or add an external endpoint.

Run focused tests with unique retained JUnit/logs inside the outer loopback-only guard, plus scoped
Ruff/format/strict mypy. No full gate, build or guest. Claim/check the assigned separate worktree,
commit only owned files, retain evidence, stop processes and return a frozen clean tip for review.
