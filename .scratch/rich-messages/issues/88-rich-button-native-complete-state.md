# Complete native rich-button state acceptance

Type: task
Status: ready-for-agent
Work state: implemented on `task/rich-button-native-complete-state`; coordinator review pending
Blocked by: coordinator integration and native execution

Own this ticket, `tests/test_runner_rich_targets.py`, `tests/rich_targets_scenario.py` and
`tests/fixtures/rich_targets_bot.py`. No production, native patch, profile, shared doc or lockfile
changes. Follow ticket74 and the frozen rich-button implementation contract.

The native status-only gate does not establish complete callback snapshots, quiet World state,
ABA rejection or event/history equality. The current unrelated phase adds two visible-chat
messages after observation and can change native geometry; accepting stale geometry would
violate the independent native freshness contract. Do not demand unsafe dispatch or accept an
unexplained union of outcomes to fit retained output.

Keep the existing full simulation scenario and expectations. Add an explicit fixture-only native
visible-effects/ABA variant ending after the stale repeat, before the unrelated-message phase.
The contained real bot and original input remain unchanged in meaning. Independently spell the
complete native expected history, callbacks, answers, receipts/effects, event ordering and quiet
before/after snapshots. Verify all six visible effects, hidden/offscreen rejections, target identity,
private native observation/effect correlation, first-call ABA rejection and immutable repeats.
Share literal canonical message/target fixtures where sound; never derive expected semantic
values from production output. Dynamic identifiers require validated shape and exact cross-binding.

Reuse the existing native entry point so the coordinator can run it against the reviewed normal27
APK. Preserve the old native result artifacts. Demonstrate useful controls rejecting wrong callback
payload/snapshot, operation-owned quiet-state mutation, wrong revision/identity, extra/missing events
and malformed native correlation using retained real results when practical. Label retained-result
checks honestly; worker execution does not establish fresh native acceptance. Run affected contained
simulation and focused host checks, native collection and scoped static checks only. No guest/build/
full gate. Return a frozen branch with terminal resources and complete handoff.

Actual clipboard paste and native unrelated-revision survival remain explicit ticket74 gaps.
The latter needs a selected-chat-preserving control flow plus real native application/draw evidence;
World acknowledgement or fixed sleeps do not establish it. Do not implement a new public API or
weaken freshness in this acceptance task.


## Implementation

The generated fixture project carries an explicit `fixture-variant.json`. Normal simulation keeps
`full`, including unrelated-edit survival. The existing Android entry point selects
`native-visible-aba`, which ends after the first stale rejection and its repeated receipt. It
never sends the unrelated-phase command or acknowledgement into the selected native chat. The
real contained bot's action and polling implementation is unchanged. Both variants additionally
retain message histories before and after each action, complementing the existing complete
identity snapshots and event arrays. The new native case reserves 16 target slots across two
observations, within the existing shared budget.

The independent native oracle requires all six exact visible effects, original target identity,
complete frozen callbacks with `answer: null`, native callback event sequences 7/8, hidden/offscreen
pre-dispatch rejection, exact clipboard pairs, immutable repeats and the first ABA revision
rejection. Each quiet action compares complete expected snapshots/events and, in the fresh
endpoint, message histories. The final native history contains exactly six messages; the selected
message's ABA revision is 11, the finish event is 13 and the two answer events are 14/15. All
callback updates, answers, history, events and relevant Bot API requests/responses are compared
against independent literal fixture values with dynamic identifiers validated and cross-bound.

Private evidence checks bind observation/effect schema, message revision, lifetime, World/persona,
canonical occurrence, touch, action and callback request. The native request ID is independently
matched to the retained read-only authoritative callback row and its creation body/answer. JSON
filenames bind their generation/content hash, and evidence paths stay in the operation directory.
The current successful operation must retain exactly its original `before.png`; the PNG must
independently decode at the fixed profile dimensions. No second capture or reconstructed native
recording is accepted as the expected current evidence.

Bot transcript comparison preserves phases and interleaving: initial delivery, both publication
writes, ordinary polls at the current offset with timeout 10, all three ABA writes immediately
after its command, finish delivery, ordered answers and one final nonblocking empty poll. Empty
ordinary waits and callback batch partitions may vary; their count/timing is not deterministic.
Their phase, offsets, delivered order and the surrounding write ordering remain exact.

## Verification and retained evidence

- `artifacts/rich-button-native-complete-state-endpoint-red.xml`: the real contained scenario
  initially ignored the requested variant and produced eight messages instead of six.
- `artifacts/rich-button-native-complete-state-final.xml`: both permanent non-Android tests pass
  under the outer network guard: the preserved full simulation and the real contained new endpoint.
  `artifacts/rich-button-native-complete-state-work/` retains their actual final runs.
- Android-only collection selects exactly the existing
  `test_public_rich_targets_prepare_original_effect_and_unavailability_evidence` entry point.
  It was collected, not executed by this worker.
- Scoped Ruff lint/format and strict mypy pass for the scenario, real bot and acceptance test.
- The ignored `.cache/native-complete-state/validate_retained.py` script runs 41 explicit controls
  against unchanged native13 evidence and a retained real contained endpoint result. The report
  `artifacts/rich-button-native-complete-state-retained.json` records original hashes and all
  controls. These include wrong callback payload/snapshot, revision/persona/path, quiet state and
  message mutations, extra/missing events, private identity/request mismatch, extra captures,
  invalid poll/write interleaving and wrong offsets/timeouts. Permitted empty waits and split or
  coalesced callback batches pass. The original native13 JSON/PNG/World database hashes remain
  unchanged. No artifact-dependent skipped tests were added to ordinary CI.
- `artifacts/rich-button-native-complete-state-interleaving-red.json` preserves the independent
  review gap: the earlier oracle accepted a publication write moved after polling. The phase
  machine now rejects that mutation without fixing the number of empty polls.

Focused reproduction from this checkout's pinned offline environment:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -q tests/test_runner_rich_targets.py -m "not android"'
tools/dev default --offline --command unshare --user --map-root-user --net \
  .venv/bin/pytest --collect-only -q -m android tests/test_runner_rich_targets.py
tools/dev default --offline --command uv run --locked --offline ruff check \
  tests/test_runner_rich_targets.py tests/rich_targets_scenario.py tests/fixtures/rich_targets_bot.py
tools/dev default --offline --command uv run --locked --offline ruff format --check \
  tests/test_runner_rich_targets.py tests/rich_targets_scenario.py tests/fixtures/rich_targets_bot.py
tools/dev default --offline --command env MYPYPATH=tests uv run --locked --offline mypy \
  --strict --explicit-package-bases tests/test_runner_rich_targets.py \
  tests/rich_targets_scenario.py tests/fixtures/rich_targets_bot.py
```

The ignored replay accepts the preserved native run directory, the actual contained result JSON
and an output report path as its three arguments; actual host paths are recorded only in ignored
evidence. Supply `PYTHONPATH=tests` under the same pinned shell/network guard. Native13 validates
only the unchanged visible/ABA prefix and is deliberately rejected as a complete new endpoint;
its unrelated traffic is never removed or relabeled as fresh ticket88 evidence. Fresh Android
execution remains coordinator-owned. Actual clipboard paste and selected-chat-preserving native
unrelated-revision survival remain explicit ticket74 gaps. No guest, build, full gate, production
API, APK, profile or rendering changes ran or were made for this task.

## Coordinator integration

Reviewed frozen tip `ae8dfe55697d0c69b92bcfd0deea955ef4a1e1ae` is integrated. Both contained
scenarios pass in 5.47 seconds on the merged worktree, with the Android case explicitly deselected,
and scoped lint/format/strict typing pass. The independent review's exact-capture and API-order
findings are resolved: precisely one original before.png is required, and a polling state machine
preserves complete write/update ordering while allowing legitimate empty waits and batching.
Evidence: `artifacts/rich-button-native-complete-state-integrated-01.xml`. Fresh native14 remains
required; retained native13 prefix validation is not full acceptance of this new endpoint.
