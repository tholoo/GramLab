# Prove original rich-button taps with a real bot in the opt-in experiment

Type: task
Status: claimed
Work state: resolved
Assigned branch: task/rich-buttons-input
Assigned worker: rich_button_seam
Blocked by: none

Use the [geometry experiment](../../../clients/android/experiments/rich-actions/README.md), frozen
[button contract](../../../docs/development/rich-buttons-contract.md) and actual admitted world
messages. Own tests/probes/android_rich_messages.py only for the two hooks below; new
tests/fixtures/rich_action_input_bot.py, tests/probes/rich_action_input_round_trip.py,
tests/probes/android_rich_action_input.py, tests/rich_action_input_experiment.py and this ticket.
The coordinator owns the GPL helper/overlay, shared docs, normal gate, APK builds and all guests.
Work in an isolated branch/worktree; no original renderer, Python core or public input API changes.

## Frozen harness seams

Extend the existing rich probe with optional keyword-only `on_configured`, called with the bridge
configuration after app-private configuration/codec setup and before the initial app launch, and
`run_scenario`, defaulting to existing `run`, with the same `(show, observe) -> result` shape.
Retain the existing `on_initial` hook. Default behavior and result shape must stay unchanged. The
new scenario runner owns a real private fixture bot and authoritative World/ClientBridge; there is
no patched validator, invented database record or native-to-world marker substitution.

The fixture bot sends exactly one top-level default callback row (`Row action`, `row:1`) and one
ordinary paragraph with an inline callback (`Inline action`, `inline:1`). Preserve short LTR
content in the existing viewport and exactly two drawn targets expected by the GPL observer. It
answers the first callback without editing, then answers the second and edits the same message
to ordinary rich completion text. Compare complete independently authored API/native content,
world history, two callbacks/answers and ordered events; keep deterministic world time explicit.
A separate simulation run may create the two callbacks through the existing World API and must
label that path as simulation. Native mode never synthesizes a callback or invokes a delegate.

The experimental probe opts in through the dedicated app-private file. Use fresh synthetic nonce,
matching snapshot world/persona and actual bot peer/message IDs. Observe unavailable output for a
wrong message identity and verify no callbacks; then activate the correct identity with a fresh
nonce and cold launch. Match process identity, nonce, message, generation and bounded guest-uptime
age, current world content and exact native callback payload before each ordinary guest tap. Read
the original native rectangles and offsets; do not calculate layout in Python. Retain a fresh
geometry sample and PNG/XML before each tap. Tap each expected center once, without retry or any
synthetic fallback. Preserve complete unexpected events and fail visibly.

Require exactly two corresponding native callbacks, real bot answers and final same-message edit,
original edited/restarted PNG/XML, successful launches, applied-edit trace, zero accounts and all
existing guest isolation checks. A missing opt-in result is a failure to observe, not a successful
negative identity check. Do not claim atomic freshness or duplicate/RTL/nested/general targeting.
Use the existing screenshot helper and reports for original, unedited evidence. Preserve callback
correlation before fast bot edits can overwrite the initial message; the expected callback message
is the actual canonical initial message at callback creation.

`tests/rich_action_input_experiment.py` is deliberately outside the default `test_*.py` filename
pattern. It must run only by explicit selection; the native function uses the android marker and
requires a separately provided experimental APK. Keep normal APK gates independent. Document exact
explicit commands in this ticket. Worker runs focused simulation and all owned Python static checks
under its pinned shell/outer network guard. It must not launch a guest or build an APK. Coordinator
runs native red/green and reviews rectangle-to-PNG correspondence with the explicit experimental
APK. Record limitations, retain evidence, commit owned files and return a frozen clean branch.

## Worker handoff

Implemented only the assigned test paths and two optional shared hooks. Default rich-probe behavior
and result shape are preserved. The new explicit host filename stays outside normal pytest
collection, and its Android case requires `GRAMLAB_RICH_ACTION_EXPERIMENT_APK`; it does not fall
back to `GRAMLAB_ANDROID_PROBE_APK`. The normal renderer, core, GPL helper and APK remain untouched.

The real isolated HTTP bot sends the two independently specified actions, then answers row without
editing and answers inline before editing the same message. Empty ordinary answers avoid adding
an unrelated popup to the geometry experiment. The controller explicitly labels simulation callback
creation; native mode calls only the supplied UI scenario. It waits for bot acknowledgement before
the next action, advances world time by five seconds per action and retains the callback's actual
initial canonical message before the second action's fast edit. Assertions compare complete HTTP
records, callback/answer bodies, native serialized content, durable history, twelve ordered events
and no pending updates or extra callbacks. Empty long-poll replies are retained and validated.

The experimental consumer writes a synthetic app-private wrong-message activation before the
initial launch, requires explicit fresh `message_not_unique_or_visible` output and an unchanged
world, then cold launches with the correct identity and a fresh nonce. It reads geometry after
retaining each original PNG/XML capture, verifies PID/nonce/identity/generation, current World and
native action bytes, and checks a five-second guest-uptime age immediately before each single
ordinary `input tap`. It records original rectangles and offsets without deriving native layout.
It does not retry input, synthesize native callbacks, trigger unrelated guest gestures or refresh
the GPL observer. The host independently checks both geometry identities and the exact two
correlated native callback request/response pairs. Existing shared capture/edit/restart logic
supplies original edited/restarted PNG/XML and applied-edit trace; report evidence includes all
five original images and isolation observations.

Verified worker evidence:

- `artifacts/rich-buttons-input-simulation-01.log` / `.xml`: focused simulation passed, one case
  in 1.81 seconds.
- `artifacts/rich-buttons-input-simulation-02.log` / `.xml`: final controller with explicit bot
  acknowledgement passed, one case in 1.47 seconds. Full scenario/API/world evidence is retained
  beneath the matching basetemp directory.
- `artifacts/rich-buttons-input-static/`: scoped Ruff/format/strict mypy for all five Python files;
  final status is recorded in the individual logs. The worker uses its own offline uv cache,
  virtual environment and Nix profile; actual local paths are in ignored verification metadata.

Explicit simulation reproduction (no guest):

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/rich_action_input_experiment.py::test_simulation_real_bot_answers_two_rich_callbacks'
```

Coordinator-only native reproduction, with `GRAMLAB_RICH_ACTION_EXPERIMENT_APK` pointing to the
separately fingerprinted experimental APK (or deliberately selected normal APK for missing-observer
red), after taking the shared gate lock:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/rich_action_input_experiment.py::test_experimental_original_row_and_inline_callback_taps'
```

Native red/green, original rectangle-to-PNG inspection and shared-probe integration acceptance
remain coordinator work. Quiet original layouts can age while capture completes: absent/stale
observation freshness fails visibly, without a helper change or fabricated sample. If this occurs,
a separately reviewed explicit app-private observation request may be needed from the coordinator.
This experiment does not establish atomic observation/touch, duplicate/nested/RTL/general targets,
copy/disabled input or a public API. No guest, build, full gate or network acquisition ran in this
worker. All worker check processes are terminal. Keep this ticket claimed until native acceptance.

## First integrated native trial

The normal-APK missing-observer trial stops before reaching the intended observer rejection.
Original PNG inspection shows both rich buttons rendered, but their labels are absent from the
original accessibility XML. Waiting for `Inline action` is therefore an invalid scene predicate.
This is a harness failure, not missing rendering or valid missing-observer red. Retained taps and
world callbacks remain empty. Add an ordinary plain-text anchor beside the inline button and use
that anchor for readiness/capture checks; retain the two native button identities and all actual
geometry/action assertions. Rerun the intended negative trial before experimental input.

## Coordinator acceptance

The integrated explicit experiment passes in 83.83 seconds on the separately fingerprinted APK.
It first launches with neither private file present and verifies unchanged World state, then
cold-launches wrong and correct identities. Wrong identity yields explicit fresh unavailability;
two original controls each receive one ordinary guest tap after independent identity/content and
freshness checks. The real bot answers both callbacks and edits the same message, with complete
native/API/history/event assertions, cold restart, zero accounts and guest isolation passing.
All six original PNGs were inspected against actual rectangles and tap centers. Desktop/mobile
report checks pass with six loaded images, no overflow and no external resources. The normal-APK
missing-observer red is retained separately from the earlier fixture-readiness failure.

The shared-probe normal regressions pass (two native cases in 169.61 seconds), as do the combined
390-test core gate and documented static/workflow checks. See the [acceptance and reproduction
record](../../../docs/development/rich-action-input-experiment.md) for exact scope and limitations.
Earlier preparation/handoff paragraphs are historical; native acceptance above resolves this
bounded ticket. Copy/disabled effects and general/public targeting remain separate work.
