# Prove original copy and disabled effects through guest input

Type: task
Status: claimed
Work state: claimed by coordinator; geometry extension delegated
Blocked by: none

Extend the accepted opt-in callback experiment to actual copy and disabled effects. This remains
outside the normal patch series and public scenario API. Preserve original renderer, accessibility,
clipboard/composer implementation and the independent MIT core. Read TESTING.md, offline safety,
licensing and the parallel workflow. No acquisition, runtime external access or real accounts.

## Frozen experimental observation extension

The activation/output schema, two-target restriction, identity, freshness and layout guards stay
unchanged. Existing callback targets retain their exact fields. Extend only the action payload:

- Callback: existing `callback_data` string; reject disabled state or password callbacks.
- Copy: `copy_text` string from the exact native copy constructor; require not disabled.
- Disabled: `disabled: true` only for the exact native disabled constructor and disabled state.

Each target has exactly one action field alongside existing kind/block/index/text and original
geometry fields. Reject all other action constructors and inconsistent state. Disabled geometry
is observation of a visible control, never permission to dispatch its action. No input, clipboard
reader, endpoint or lifecycle change is assigned to the GPL helper.

Geometry worker owns only `clients/android/experiments/rich-actions/RichActionGeometryProbe.java`
and this ticket's worker evidence section. Work on `task/rich-effect-geometry` in its own checkout.
Inspect the pinned source types, implement the exact extension and compile against cached pinned
SDK/client inputs. Do not build an APK or launch a guest. Coordinator owns experiment README,
Python harness, other docs, experimental build, native acceptance and merges. Return a frozen clean
branch, source review and terminal check evidence; keep the ticket claimed until native acceptance.

## Native fixture and acceptance owned by coordinator

A real isolated HTTP bot sends one top-level row copy button and one paragraph with ordinary
`Choose:` text and an inline disabled button. Use a distinctive ASCII clipboard payload. Require
complete independently specified Bot API/native/history/events before and after ordinary input.
The bot acknowledges the initial update; copy and disabled actions create no callback/update/edit.
A simulation fixture proves shared API/state only and must not invent a simulated clipboard effect.

Retain the no-opt-in and wrong-message negative lifecycle checks. On the correct cold launch,
match exact native content, current World state, nonce/process/generation and bounded age after
original PNG/XML capture, then tap each observed target once without retry. After copy, focus the
original composer and use ordinary guest paste; its XML must contain the exact copied payload.
Clear the draft without sending. After disabled, repeat paste and require the same clipboard text.
At each checkpoint compare complete World snapshot/events, pending updates and actual bot transcript;
no action-producing HTTP calls or native callback trace may occur. Retain original copy feedback
when observable without turning unproven transient bulletin timing into a readiness predicate.

The paste key event is an experiment, not established behavior. If it fails, preserve the actual
failure and investigate original guest paste gestures; do not add a clipboard-reading backdoor.
Cold restart must retain the original message and an empty composer. Preserve zero accounts,
local-only reachability, external IPv4/IPv6 denial and component filesystem separation. Inspect
original PNGs against observed bounds, copied text and disabled styling.

Run scoped Python static checks and simulation, separate offline experimental APK build and the
explicit native fixture under existing locks. The callback fixture must pass on the extended helper
because its shared action-validation code changed. Keep normal APK evidence separate. Record exact
failures, successful checks, fingerprint and process state in ignored artifacts; reconcile public
docs and compatibility only after actual native proof. Public targeting, RTL/nesting, duplicate or
stale edits, both placements of every action and long-press remain wider inventory work.

## Geometry worker evidence

The delegated GPL helper extension preserves callback output and emits exactly one action field
for each admitted native constructor: callback data, copied text or `disabled: true`. It rejects
password callbacks, null copied text, unsupported constructors and every inconsistent disabled
state. The existing identity, freshness, two-target, layout and geometry behavior is unchanged.
Coordinator-owned native input remains required before resolving this ticket.

Source review used the pinned `TL_keyboard` definitions from the immutable normal source export.
A focused JDK 17 compile against Android 36, the previously compiled pinned client classes and
cached AndroidX jars produced `RichActionGeometryProbe.class`. It completed with 39 pre-existing
dependency-annotation/serial warnings and no errors. The first narrower classpath attempt failed
before compilation could complete because `LaunchActivity`'s AndroidX superclass was absent; the
corrected cached classpath resolved it. No APK, guest, bot, network or shared resource lock ran.

## Integrated preparation

The reviewed geometry worker is merged after the separate offline APK builds in 2 minutes
32 seconds (78 tasks, 9 executed and 69 up to date). The normal source/APK are unchanged. The
real-bot effect fixture passes simulation (final scoped run: one case in 1.09 seconds), with four
Python files passing lint/format/strict typing. Its first simulation attempt exposed an incorrect
fixture snapshot expectation: the documented version-2 snapshot uses `schema` and includes
`message_position`/`sends`; the corrected complete expectation passes. No production behavior changed.
The updated manual workflow passes its pinned offline check.

The preceding callback-only experimental APK rejects the same copy/disabled fixture in 102.51
seconds. Absent opt-in and wrong-message phases pass; correct identity produces explicit
`initial_experiment_requires_callback` observations, and input is never attempted. Zero taps and
unchanged authoritative state are retained. The original initial PNG was inspected and shows the
native copy icon and dimmed disabled inline control. This is valid observation-refusal evidence,
not a clipboard or disabled-effect pass. The new APK's native effect acceptance and callback
regression remain pending; ticket stays claimed.

Explicit simulation reproduction:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/rich_action_effect_experiment.py::test_simulation_real_bot_copy_disabled_content_without_ui_effects'
```

With `GRAMLAB_RICH_ACTION_EXPERIMENT_APK` pointing to the separately built experimental APK,
run the native fixture explicitly under the shared lock and offline guard:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/rich_action_effect_experiment.py::test_experimental_original_copy_and_disabled_effects'
```


The first new-APK native trial fails in 79.95 seconds after one real copy tap. Its original PNG
shows Android's clipboard overlay displaying the copied payload over the composer. The harness's
redundant composer-center tap hits that overlay's Share control; the next XML is the original
system share sheet. Both preceding XML captures show the original composer already focused.
This is a harness focus error, not clipboard-paste acceptance. Require that existing original
focus and issue the ordinary paste key directly; retain exact text/deletion checks and no input
retry. Move the capture's scene predicate after saving PNG so a failed scene retains both PNG/XML.


The next native trial fails in 85.75 seconds after proving the exact copied payload in the
original composer through the ordinary paste key, followed by successful ordinary deletion.
Original pasted/cleared PNGs and XML were inspected. No IME was opened. The retained cleared XML
has focus, while the next pre-disabled XML lacks it: the harness's unnecessary Escape key between
those captures cleared focus. Remove that keypress and retain strict focus/paste checks. The
second disabled-phase paste and cold restart remain unaccepted until a full native pass.
