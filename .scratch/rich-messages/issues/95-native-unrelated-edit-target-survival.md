# Prove native rich targets survive an unrelated same-layout edit

Type: task
Status: ready-for-agent
Work state: claimed by `native_unrelated_target_survival` on `task/native-unrelated-edit-target-survival`
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

## Implementation

The new contained bot publishes message A with one visible callback row followed by one-line
message B. A second synthetic user owns a separate private control chat. Only that control chat
requests B's one-line `alpha` → `bravo` edit and receives its acknowledgement; the rendered chat
receives no new message. The public scenario retains A's first target ID, taps it once after the
acknowledgement, repeats the same receipt, then uses a separate observation to prove a real edit of
A rejects its old target before dispatch. Complete snapshots, events, both histories, frozen
callback and answer are independently specified for simulation and native modes.

The test-only supervisor wraps the existing Android rich-input seam. It retains the first native
observation's message/revision, process nonce, PID and geometry. Immediately before the original
`prepare`, it calls the existing `Android._wait_ui` for B's edited text in the already-running
selected chat, checks zero accounts and retains the original XML/PNG. It does not open, capture or
re-observe the chat. The original prepare must then report the same process, lifetime and geometry;
an ADB call counter rejects any guest call between prepare's return and dispatch. The host staging
control pins this supervisor as the sole native entry override and rejects a scenario re-observation
between the unrelated edit request and original target tap.

The review follow-up shares one complete contained-bot transcript oracle between simulation and
native expectations. It compares both publication results, all command/callback updates, every
edit/acknowledgement/answer response, causal polling offsets and the final empty drain. Only empty
long-poll results are variable inside the four causally separated phases; unknown updates, writes
or reordered writes reject. The native oracle now validates exact retained JSON schemas and hashed
paths, full message/process/lifetime/generation/timing/geometry/touch/request identity, callback
request ID/body/revision against SQLite and both original PNGs. The executed bootstrap records a
hash of its own staged bytes. Its ADB wrapper records every `shell input tap`; acceptance requires
exactly one tap at the retained target center while preserving the zero-call prepare/dispatch gap.

## Worker verification

- `artifacts/ticket95-final.xml`: two focused non-Android cases pass in the isolated local network:
  the real contained public simulation and the supervisor source/staging control. One Android case
  is deselected.
- Scoped Ruff check/format and strict mypy with explicit package bases pass for all four new files.
- Android-only collection selects exactly one case. Original Android execution is coordinator-owned
  and remains pending; no guest, APK build, profile, timeout or existing test ran or changed here.
- The review follow-up reran the canonical contained non-Android command: both focused cases pass.
  Scoped Ruff check/format and strict mypy again pass all four files. The expanded Android case was
  collected only; its stronger native/API/provenance expectations remain pending coordinator guest
  execution.
- Early `ticket95-simulation-red.xml` and `ticket95-simulation-green.xml` retain two test-oracle
  projection failures discovered while authoring the independent expected state. They are not
  claimed as behavioral reds; no production behavior changed in this test-only task.

Reproduction uses the assigned checkout's `.venv` and immutable primary uv cache:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -q tests/test_runner_unrelated_target.py -m "not android"'
tools/dev default --offline --command uv run --locked --offline ruff check \
  tests/test_runner_unrelated_target.py tests/unrelated_target_scenario.py \
  tests/fixtures/unrelated_target_bot.py tests/probes/unrelated_target_supervisor.py
tools/dev default --offline --command env MYPYPATH=tests uv run --locked --offline mypy \
  --strict --explicit-package-bases tests/test_runner_unrelated_target.py \
  tests/unrelated_target_scenario.py tests/fixtures/unrelated_target_bot.py \
  tests/probes/unrelated_target_supervisor.py
```
