# Prove native rich targets survive an unrelated same-layout edit

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Own this ticket and new `tests/fixtures/unrelated_target_bot.py`,
`tests/unrelated_target_scenario.py`, `tests/probes/unrelated_target_supervisor.py`,
`tests/test_runner_unrelated_target.py` only. No production, existing fixtures/tests, native patch,
profile, shared docs, deadlines or observation/dispatch guard changes. Follow74/88 and the approved
rich-button targeting contract. Coordinator owns guest execution and integration.

A different message revision must not invalidate an observed target by itself, but current native
geometry/focus/lifetime constraints remain authoritative. The former full fixture adds visible
messages and moves the selected cell, so that rejection is not a valid positive control for an
unrelated edit that leaves the target in the same place.

Build a minimal real-bot scenario with one rendered private chat and a separate control chat. The
bot publishes a visible rich callback target in message A plus an unrelated visible message B.
Observe A once through the public rich-target operation. Request a same-height edit of B through
the real bot using only the control chat; acknowledge completion there, without adding anything
to the rendered chat. Preserve A content/revision, selected persona/chat, viewport, client lifetime
and the original target handle. Then tap that original handle exactly once and assert the actual
callback plus its answer and complete final semantic state.

World acknowledgement alone is insufficient to establish native application. Use a bounded test-
only supervisor to wait for B's distinguishable edited text in the actual existing Android UI,
and retain original XML/PNG, before original target preparation starts. Reuse the existing guest
UI observation helper without calling _open_chat/capture APIs that force-stop/reopen the app.
Do not re-observe or mint a new target, refresh its lifetime, sleep for assumed settlement, inspect
only World/backend ACKs, or insert any guest calls between original prepare and dispatch. If B's
new visible text cannot be independently observed without changing the tested state, report the
exact missing observation instead of replacing it with synthetic success.

Pair the native positive with a genuine related-edit rejection: change A after observation through
the real bot and show the old handle rejects before dispatch with no callback. Keep this distinct
from the positive unrelated case, using complete independently specified states and ordinary real
API updates. Also retain repeated-receipt idempotence after the successful callback. The core
contract must work in simulation with the same scenario semantics; simulation cannot prove UI
survival. Native checks must establish original target/message/process/lifetime provenance,
unchanged geometry, actual touch/callback, zero accounts, network/filesystem isolation and original
captures. Preserve negative evidence and do not weaken guards if the positive fails.

Write focused public simulation expectations and host controls for the bounded UI barrier and
source staging; run red/green at their real relevant interfaces. No guest/build/full gate assigned.
Keep helper code limited to this proof. Return clean frozen branch, actual focused checks and
explicit pending original Android acceptance; use only the small assigned environment.
