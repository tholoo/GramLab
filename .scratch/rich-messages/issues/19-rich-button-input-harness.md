# Prove original rich-button taps with a real bot in the opt-in experiment

Type: task
Status: ready-for-agent
Work state: open
Blocked by: ticket 17 experimental APK for native execution

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
